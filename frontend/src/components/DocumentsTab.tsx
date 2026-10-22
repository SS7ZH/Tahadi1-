import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarClock, CheckCircle2, FileText, HeartPulse, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { documentsApi } from '@/api/endpoints';
import type { SignedDocumentInfo, SubscriptionInfo } from '@/api/types';
import { useDocuments, useHealth, useStaffPlans, useSubscriptions } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { fmtDate, todayISO } from '@/lib/format';
import { DeclarationView, SignedDocList, SignedDocModal } from './documents';
import { Badge, Button, Card, CardHeader, Input, Modal, Select, Skeleton } from './ui';

function useInvalidate(clientId: number) {
  const qc = useQueryClient();
  return () => Promise.all([qc.invalidateQueries({ queryKey: ['client', clientId] }), qc.invalidateQueries({ queryKey: ['clients'] })]);
}

function SubscriptionRow({ s }: { s: SubscriptionInfo }) {
  return (
    <li className="flex flex-wrap items-center gap-2 px-4 py-2.5 text-sm sm:px-5">
      <span className="font-semibold">{loc(s.plan_name_ar, s.plan_name_en)}</span>
      <Badge>{tr.subscriptionKind[s.kind]}</Badge>
      <span className="text-muted">
        {fmtDate(s.start_date)} – {fmtDate(s.end_date)}
      </span>
      <span className="ms-auto">
        {s.contract_signed ? <Badge tone="good">{tr.documents.contractSigned}</Badge> : <Badge tone="warn">{tr.documents.contractPending}</Badge>}
      </span>
    </li>
  );
}

function RenewModal({ clientId, onClose }: { clientId: number; onClose: () => void }) {
  const plans = useStaffPlans();
  const invalidate = useInvalidate(clientId);
  const [planId, setPlanId] = useState('');
  const [start, setStart] = useState(todayISO());
  const [kind, setKind] = useState<'renewal' | 'change'>('renewal');
  const save = useMutation({
    mutationFn: () => documentsApi.renew(clientId, { plan_id: Number(planId), start_date: start, kind }),
    onSuccess: async () => {
      toast.success(tr.documents.renewed);
      await invalidate();
      onClose();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <Modal
      open
      onClose={onClose}
      title={tr.documents.renew}
      size="sm"
      footer={
        <Button disabled={!planId || !start} loading={save.isPending} onClick={() => save.mutate()}>
          {tr.common.save}
        </Button>
      }
    >
      <div className="flex flex-col gap-3">
        <Select label={tr.documents.kindLabel} value={kind} onChange={(e) => setKind(e.target.value as 'renewal' | 'change')}>
          <option value="renewal">{tr.subscriptionKind.renewal}</option>
          <option value="change">{tr.subscriptionKind.change}</option>
        </Select>
        <Select label={tr.onboarding.choosePlan} value={planId} onChange={(e) => setPlanId(e.target.value)}>
          <option value="">{tr.form.choose}</option>
          {plans.data?.map((p) => (
            <option key={p.id} value={p.id}>
              {loc(p.name_ar, p.name_en)}
              {p.price != null ? ` · ${p.price} ${p.currency}` : ''}
            </option>
          ))}
        </Select>
        <Input label={tr.onboarding.startDate} type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        <p className="text-xs text-muted">{tr.documents.renewHint}</p>
      </div>
    </Modal>
  );
}

function DatesModal({ clientId, sub, onClose }: { clientId: number; sub: SubscriptionInfo; onClose: () => void }) {
  const invalidate = useInvalidate(clientId);
  const [start, setStart] = useState(sub.start_date);
  const [end, setEnd] = useState(sub.end_date);
  const save = useMutation({
    mutationFn: () => documentsApi.updateSubscription(sub.id, { start_date: start, end_date: end }),
    onSuccess: async () => {
      toast.success(tr.documents.datesSaved);
      await invalidate();
      onClose();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <Modal
      open
      onClose={onClose}
      title={tr.documents.editDates}
      size="sm"
      footer={
        <Button disabled={!start || !end || end < start} loading={save.isPending} onClick={() => save.mutate()}>
          {tr.common.save}
        </Button>
      }
    >
      <div className="grid grid-cols-2 gap-3">
        <Input label={tr.onboarding.startDate} type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        <Input label={tr.onboarding.endDate} type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} />
      </div>
    </Modal>
  );
}

export function DocumentsTab({ clientId }: { clientId: number }) {
  const subs = useSubscriptions(clientId);
  const health = useHealth(clientId);
  const docs = useDocuments(clientId);
  const invalidate = useInvalidate(clientId);
  const [modal, setModal] = useState<'renew' | 'dates' | null>(null);
  const [openDoc, setOpenDoc] = useState<SignedDocumentInfo | null>(null);
  const review = useMutation({
    mutationFn: () => documentsApi.review(clientId),
    onSuccess: invalidate,
    onError: (e) => toast.error(errorMessage(e)),
  });
  const sub = subs.data?.current;

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          title={tr.documents.subscription}
          icon={<CalendarClock className="h-5 w-5" />}
          actions={
            <>
              {sub && (
                <Button size="sm" variant="outline" onClick={() => setModal('dates')}>
                  {tr.documents.editDates}
                </Button>
              )}
              <Button size="sm" icon={<RefreshCw className="h-4 w-4" />} onClick={() => setModal('renew')}>
                {tr.documents.renew}
              </Button>
            </>
          }
        />
        {subs.isLoading ? (
          <Skeleton className="m-5 h-16" />
        ) : sub ? (
          <>
            <div className="flex flex-wrap items-center gap-3 border-b border-line px-4 py-3 sm:px-5">
              <div className="flex-1">
                <p className="font-bold">{loc(sub.plan_name_ar, sub.plan_name_en)}</p>
                <p className="text-sm text-muted">
                  {fmtDate(sub.start_date)} – {fmtDate(sub.end_date)}
                  {sub.price != null && ` · ${sub.price} ${sub.currency}`}
                </p>
              </div>
              <Badge tone={sub.status === 'expired' ? 'bad' : sub.status === 'upcoming' ? 'warn' : 'good'}>
                {sub.status === 'active' ? tr.documents.daysLeft(Math.max(0, sub.days_left ?? 0)) : tr.subscriptionStatus[sub.status ?? 'active']}
              </Badge>
            </div>
            <ul className="divide-y divide-line">
              {subs.data!.history.map((s) => (
                <SubscriptionRow key={s.id} s={s} />
              ))}
            </ul>
          </>
        ) : (
          <p className="p-4 text-sm text-muted">{tr.documents.contractPending}</p>
        )}
      </Card>

      <Card>
        <CardHeader
          title={tr.documents.health}
          icon={<HeartPulse className="h-5 w-5" />}
          actions={
            health.data?.needs_review ? (
              <Button size="sm" variant="secondary" icon={<CheckCircle2 className="h-4 w-4" />} loading={review.isPending} onClick={() => review.mutate()}>
                {tr.documents.markReviewed}
              </Button>
            ) : undefined
          }
        />
        <div className="flex flex-col gap-4 p-4 sm:p-5">
          {health.isLoading ? (
            <Skeleton className="h-20" />
          ) : health.data?.current ? (
            <>
              {health.data.needs_review && <Badge tone="warn">{tr.documents.updatedBadge}</Badge>}
              <DeclarationView d={health.data.current} />
              {health.data.history.length > 1 && (
                <details className="rounded-xl border border-line p-3">
                  <summary className="cursor-pointer text-sm font-semibold">{tr.documents.healthHistory}</summary>
                  <div className="mt-3 flex flex-col gap-4">
                    {health.data.history.slice(1).map((d) => (
                      <div key={d.id} className="border-t border-line pt-3">
                        <DeclarationView d={d} />
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </>
          ) : (
            <p className="text-sm text-muted">{tr.documents.noHealth}</p>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title={tr.documents.signedDocs} icon={<FileText className="h-5 w-5" />} />
        {docs.isLoading ? <Skeleton className="m-5 h-16" /> : <SignedDocList docs={docs.data ?? []} onOpen={setOpenDoc} />}
      </Card>

      {modal === 'renew' && <RenewModal clientId={clientId} onClose={() => setModal(null)} />}
      {modal === 'dates' && sub && <DatesModal clientId={clientId} sub={sub} onClose={() => setModal(null)} />}
      <SignedDocModal doc={openDoc} onClose={() => setOpenDoc(null)} />
    </div>
  );
}
