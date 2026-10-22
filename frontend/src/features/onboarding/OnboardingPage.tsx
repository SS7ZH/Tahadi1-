import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';
import { CheckCircle2, LogOut } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { onboardingApi } from '@/api/endpoints';
import type { HealthInput, OnboardingStatus, Plan } from '@/api/types';
import { emptyHealth, HealthForm } from '@/components/documents';
import { LanguageSwitch } from '@/components/LanguageSwitch';
import { Logo } from '@/components/Logo';
import { Button, Card, ErrorState, Input, Skeleton } from '@/components/ui';
import { useAuth, useCurrentUser } from '@/hooks/useAuth';
import { qk, useOnboarding } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { fmtDate, todayISO } from '@/lib/format';
import { FullScreenLoader } from '@/routes/RequireRole';

function addMonthsISO(start: string, months: number): string {
  const [y, m, d] = start.split('-').map(Number);
  const target = new Date(y, m - 1 + months, 1);
  const last = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate();
  target.setDate(Math.min(d, last));
  target.setDate(target.getDate() - 1);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}`;
}

const price = (p: Plan) => (p.price != null ? `${p.price.toLocaleString('en-US')} ${p.currency}` : tr.onboarding.noPrice);

function Stepper({ step }: { step: number }) {
  return (
    <ol className="mb-5 grid grid-cols-3 gap-2">
      {tr.onboarding.steps.map((label, i) => {
        const n = i + 1;
        const done = n < step;
        return (
          <li key={label} className="flex flex-col gap-1.5">
            <span className={clsx('h-1.5 rounded-full', n <= step ? 'bg-primary' : 'bg-line')} />
            <span className={clsx('flex items-center gap-1 text-xs font-semibold', n === step ? 'text-primary' : 'text-muted')}>
              {done && <CheckCircle2 className="h-3.5 w-3.5 text-good" />}
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function StepSubscription({ status, onDone }: { status: OnboardingStatus; onDone: () => void }) {
  const [planId, setPlanId] = useState<number | null>(status.plans[0]?.id ?? null);
  const [start, setStart] = useState(todayISO());
  const plan = status.plans.find((p) => p.id === planId);
  const save = useMutation({
    mutationFn: () => onboardingApi.chooseSubscription(planId!, start),
    onSuccess: onDone,
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-bold">{tr.onboarding.choosePlan}</h2>
      <div className="grid grid-cols-2 gap-3">
        {status.plans.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => setPlanId(p.id)}
            aria-pressed={planId === p.id}
            className={clsx('rounded-2xl border p-4 text-start transition', planId === p.id ? 'border-primary bg-primary/10 ring-2 ring-primary/20' : 'border-line hover:bg-surface-2')}
          >
            <p className="font-bold">{loc(p.name_ar, p.name_en)}</p>
            <p className="mt-1 text-sm text-muted">{price(p)}</p>
          </button>
        ))}
      </div>
      <Input label={tr.onboarding.startDate} type="date" min={todayISO()} value={start} onChange={(e) => setStart(e.target.value)} />
      {plan && start && (
        <div className="grid grid-cols-2 gap-3 rounded-xl bg-surface-2 p-3 text-sm">
          <div>
            <p className="text-xs text-muted">{tr.onboarding.endDate}</p>
            <p className="font-semibold">{fmtDate(addMonthsISO(start, plan.months))}</p>
          </div>
          <div>
            <p className="text-xs text-muted">{tr.onboarding.price}</p>
            <p className="font-semibold">{price(plan)}</p>
          </div>
        </div>
      )}
      <p className="text-xs text-muted">{tr.onboarding.planLocked}</p>
      <Button size="lg" disabled={!planId || !start || start < todayISO()} loading={save.isPending} onClick={() => save.mutate()}>
        {tr.onboarding.continue}
      </Button>
    </div>
  );
}

function SignatureFields({ name, agreed, setAgreed, typed, setTyped, enabled = true }: { name: string; agreed: boolean; setAgreed: (v: boolean) => void; typed: string; setTyped: (v: string) => void; enabled?: boolean }) {
  return (
    <div className="flex flex-col gap-3">
      <label className={clsx('flex items-center gap-2 text-sm font-semibold', !enabled && 'opacity-50')}>
        <input type="checkbox" checked={agreed} disabled={!enabled} onChange={(e) => setAgreed(e.target.checked)} className="h-5 w-5 accent-[rgb(var(--c-primary))]" />
        {tr.onboarding.agreeRead}
      </label>
      <Input label={tr.onboarding.typedName} hint={tr.onboarding.typedNameHint(name)} value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="name" dir="auto" />
    </div>
  );
}

function StepHealth({ status, onDone }: { status: OnboardingStatus; onDone: () => void }) {
  const user = useCurrentUser();
  const qc = useQueryClient();
  const disclaimer = useQuery({ queryKey: ['onboarding', 'disclaimer'], queryFn: onboardingApi.disclaimer });
  const [health, setHealth] = useState<HealthInput>(emptyHealth);
  const [agreed, setAgreed] = useState(false);
  const [typed, setTyped] = useState('');
  const files = status.pending_files;

  const submit = useMutation({
    mutationFn: () =>
      onboardingApi.submitHealth({ ...health, file_ids: files.map((f) => f.id), template_id: disclaimer.data!.template_id, typed_name: typed, agreed }),
    onSuccess: onDone,
    onError: (e) => {
      toast.error(errorMessage(e));
      disclaimer.refetch();
    },
  });
  const needsDetails = health.has_chronic && (!health.conditions.length || !(health.details ?? '').trim());

  return (
    <div className="flex flex-col gap-5">
      <HealthForm
        value={health}
        onChange={setHealth}
        files={files}
        onUpload={async (f) => {
          try {
            await onboardingApi.uploadFile(f);
            toast.success(tr.onboarding.uploaded);
            await qc.invalidateQueries({ queryKey: qk.onboarding });
          } catch (e) {
            toast.error(errorMessage(e));
          }
        }}
        onRemoveFile={async (id) => {
          await onboardingApi.removeFile(id);
          await qc.invalidateQueries({ queryKey: qk.onboarding });
        }}
      />
      <div>
        <h3 className="mb-2 font-bold">{tr.onboarding.disclaimer}</h3>
        {disclaimer.isLoading ? (
          <Skeleton className="h-48" />
        ) : (
          <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-xl border border-line bg-surface-2 p-4 font-sans text-sm leading-relaxed">{disclaimer.data?.text}</pre>
        )}
      </div>
      <SignatureFields name={user.full_name} agreed={agreed} setAgreed={setAgreed} typed={typed} setTyped={setTyped} />
      <Button size="lg" disabled={!agreed || !typed.trim() || needsDetails || !disclaimer.data} loading={submit.isPending} onClick={() => submit.mutate()}>
        {tr.onboarding.signHealth}
      </Button>
    </div>
  );
}

function StepContract({ onDone }: { onDone: () => void }) {
  const user = useCurrentUser();
  const contract = useQuery({ queryKey: ['onboarding', 'contract'], queryFn: onboardingApi.contract });
  const box = useRef<HTMLPreElement>(null);
  const [scrolledToEnd, setScrolledToEnd] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [typed, setTyped] = useState('');

  const checkScroll = () => {
    const el = box.current;
    if (el && el.scrollTop + el.clientHeight >= el.scrollHeight - 8) setScrolledToEnd(true);
  };
  useEffect(() => {
    // short texts that fit without scrolling count as read
    const t = setTimeout(checkScroll, 50);
    return () => clearTimeout(t);
  }, [contract.data]);

  const sign = useMutation({
    mutationFn: () => onboardingApi.signContract({ template_id: contract.data!.template_id, typed_name: typed, agreed }),
    onSuccess: onDone,
    onError: (e) => {
      toast.error(errorMessage(e));
      setScrolledToEnd(false);
      setAgreed(false);
      contract.refetch();
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-bold">{tr.onboarding.contract}</h2>
      {contract.isLoading ? (
        <Skeleton className="h-80" />
      ) : contract.error ? (
        <ErrorState message={errorMessage(contract.error)} onRetry={() => contract.refetch()} />
      ) : (
        <pre ref={box} onScroll={checkScroll} tabIndex={0} className="max-h-[50vh] overflow-auto whitespace-pre-wrap rounded-xl border border-line bg-surface-2 p-4 font-sans text-sm leading-relaxed">
          {contract.data?.text}
        </pre>
      )}
      {!scrolledToEnd && <p className="text-xs font-semibold text-warn">{tr.onboarding.scrollToEnd}</p>}
      <SignatureFields name={user.full_name} agreed={agreed} setAgreed={setAgreed} typed={typed} setTyped={setTyped} enabled={scrolledToEnd} />
      <Button size="lg" disabled={!scrolledToEnd || !agreed || !typed.trim()} loading={sign.isPending} onClick={() => sign.mutate()}>
        {tr.onboarding.sign}
      </Button>
    </div>
  );
}

/** Required 3-step wizard on a player's first login (and again for a new contract after renewal). */
export function OnboardingPage() {
  const user = useCurrentUser();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const status = useOnboarding();

  if (user.role !== 'client') return <Navigate to="/" replace />;
  if (status.isLoading) return <FullScreenLoader />;
  if (status.error || !status.data) return <ErrorState message={errorMessage(status.error)} onRetry={() => status.refetch()} />;
  if (status.data.complete) return <Navigate to="/me" replace />;

  const next = async () => {
    const fresh = await qc.fetchQuery({ queryKey: qk.onboarding, queryFn: onboardingApi.status, staleTime: 0 });
    if (fresh.complete) {
      toast.success(tr.onboarding.done);
      await qc.invalidateQueries();
      navigate('/me', { replace: true });
    }
  };
  const step = status.data.step ?? 1;

  return (
    <div className="min-h-screen bg-bg">
      <header className="flex items-center justify-between border-b border-line bg-surface px-4 py-3">
        <Logo />
        <div className="flex items-center gap-1">
          <LanguageSwitch compact />
          <Button variant="ghost" size="sm" icon={<LogOut className="h-4 w-4" />} onClick={logout}>
            {tr.onboarding.logout}
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-2xl px-4 py-6">
        <h1 className="text-2xl font-bold">{tr.onboarding.title}</h1>
        <p className="mb-5 mt-1 text-sm text-muted">{tr.onboarding.subtitle}</p>
        <Stepper step={step} />
        <Card className="p-4 sm:p-6">
          <p className="mb-4 text-xs font-semibold text-muted">{tr.onboarding.step(step)}</p>
          {step === 1 && <StepSubscription status={status.data} onDone={next} />}
          {step === 2 && <StepHealth status={status.data} onDone={next} />}
          {step === 3 && <StepContract onDone={next} />}
        </Card>
      </main>
    </div>
  );
}
