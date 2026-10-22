import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import clsx from 'clsx';
import { Activity, ChevronDown, Gauge, HeartPulse, Ruler, Save } from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';
import { useForm, useWatch, type Control, type UseFormRegister, type FieldErrors } from 'react-hook-form';
import { toast } from 'sonner';
import { z } from 'zod';
import { errorMessage } from '@/api/client';
import { clientsApi, sessionsApi } from '@/api/endpoints';
import {
  CATEGORIES,
  type Category,
  type Definition,
  type Session,
  type SessionDetail,
  type SummaryValue,
  type ValueInput,
} from '@/api/types';
import { useDefinitions, useInvalidateClient, useSummary } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { todayISO } from '@/lib/format';
import { Button, Card, ErrorState, Input, Skeleton, Textarea } from './ui';

const BP = { systolic: [60, 260], diastolic: [30, 160] } as const;

interface Cell {
  n: string; // number / choice value / systolic
  t: string; // text / choice notes
  d: string; // diastolic
}
interface FormValues {
  session_date: string;
  notes: string;
  values: Record<string, Cell>;
}

const categoryIcon: Record<Category, ReactNode> = {
  vital: <HeartPulse className="h-5 w-5" />,
  body: <Ruler className="h-5 w-5" />,
  movement: <Activity className="h-5 w-5" />,
  physical: <Gauge className="h-5 w-5" />,
};

const toNum = (s: string) => (s.trim() === '' ? null : Number(s.replace(',', '.')));

function buildSchema(defs: Definition[]) {
  const cell = z.object({ n: z.string(), t: z.string(), d: z.string() });
  return z
    .object({
      session_date: z
        .string()
        .min(1, tr.form.dateRequired)
        .refine((v) => v <= todayISO(), tr.form.futureDate),
      notes: z.string().max(5000),
      values: z.record(cell),
    })
    .superRefine((data, ctx) => {
      for (const d of defs) {
        const c = data.values[d.key];
        if (!c) continue;
        const path = ['values', d.key, 'n'];
        if (d.value_type === 'number') {
          const v = toNum(c.n);
          if (v === null) continue;
          if (Number.isNaN(v)) ctx.addIssue({ code: 'custom', path, message: tr.form.invalidNumber });
          else if ((d.min_value !== null && v < d.min_value) || (d.max_value !== null && v > d.max_value))
            ctx.addIssue({ code: 'custom', path, message: tr.form.rangeError(loc(d.name_ar, d.name_en), d.min_value ?? 0, d.max_value ?? 0) });
        }
        if (d.value_type === 'blood_pressure') {
          const s = toNum(c.n);
          const di = toNum(c.d);
          if (s === null && di === null) continue;
          if (s === null || di === null || Number.isNaN(s) || Number.isNaN(di))
            ctx.addIssue({ code: 'custom', path, message: tr.form.bpBoth });
          else if (s < BP.systolic[0] || s > BP.systolic[1])
            ctx.addIssue({ code: 'custom', path, message: tr.form.rangeError(tr.form.systolic, BP.systolic[0], BP.systolic[1]) });
          else if (di < BP.diastolic[0] || di > BP.diastolic[1])
            ctx.addIssue({ code: 'custom', path, message: tr.form.rangeError(tr.form.diastolic, BP.diastolic[0], BP.diastolic[1]) });
          else if (di >= s) ctx.addIssue({ code: 'custom', path, message: tr.form.bpOrder });
        }
      }
    });
}

function initialValues(defs: Definition[], session?: Session | null): FormValues {
  const values: Record<string, Cell> = {};
  for (const d of defs) {
    const v = session?.values.find((x) => x.key === d.key);
    values[d.key] = {
      n:
        d.value_type === 'blood_pressure'
          ? String(v?.value_json?.systolic ?? '')
          : v?.value_number !== null && v?.value_number !== undefined
            ? String(v.value_number)
            : '',
      t: v?.value_text ?? '',
      d: d.value_type === 'blood_pressure' ? String(v?.value_json?.diastolic ?? '') : '',
    };
  }
  return { session_date: session?.session_date ?? todayISO(), notes: session?.notes ?? '', values };
}

function toPayload(defs: Definition[], data: FormValues): ValueInput[] {
  const out: ValueInput[] = [];
  for (const d of defs) {
    const c = data.values[d.key];
    if (!c) continue;
    if (d.value_type === 'number') {
      const v = toNum(c.n);
      if (v !== null) out.push({ key: d.key, value_number: v });
    } else if (d.value_type === 'choice') {
      const v = toNum(c.n);
      if (v !== null) out.push({ key: d.key, value_number: v, value_text: c.t.trim() || null });
    } else if (d.value_type === 'text') {
      if (c.t.trim()) out.push({ key: d.key, value_text: c.t.trim() });
    } else if (d.value_type === 'blood_pressure') {
      const s = toNum(c.n);
      const di = toNum(c.d);
      if (s !== null && di !== null) out.push({ key: d.key, systolic: s, diastolic: di });
    }
  }
  return out;
}

function isFilled(d: Definition, c?: Cell) {
  if (!c) return false;
  return d.value_type === 'text' ? !!c.t.trim() : !!c.n.trim();
}

function FieldInput({
  def,
  previous,
  register,
  errors,
}: {
  def: Definition;
  previous?: SummaryValue;
  register: UseFormRegister<FormValues>;
  errors: FieldErrors<FormValues>;
}) {
  const err = errors.values?.[def.key]?.n?.message;
  const prevText = previous ? previous.display : undefined;
  const hint = prevText ? (
    <span>
      {tr.common.previous}: <span className="num font-semibold text-ink/80">{prevText}</span>
    </span>
  ) : undefined;

  if (def.value_type === 'blood_pressure') {
    const [ps, pd] = prevText?.split('/') ?? [];
    return (
      <div className="flex flex-col gap-1.5 sm:col-span-2">
        <span className="text-sm font-medium">
          {loc(def.name_ar, def.name_en)} <span className="text-xs text-muted">({loc(def.unit, def.unit_en)})</span>
        </span>
        <div className="grid grid-cols-2 gap-2">
          <Input
            aria-label={`${loc(def.name_ar, def.name_en)} ${tr.form.systolic}`}
            type="number"
            inputMode="numeric"
            dir="ltr"
            placeholder={ps ?? tr.form.systolic}
            suffix={tr.form.systolic}
            {...register(`values.${def.key}.n`)}
          />
          <Input
            aria-label={`${loc(def.name_ar, def.name_en)} ${tr.form.diastolic}`}
            type="number"
            inputMode="numeric"
            dir="ltr"
            placeholder={pd ?? tr.form.diastolic}
            suffix={tr.form.diastolic}
            {...register(`values.${def.key}.d`)}
          />
        </div>
        {err ? <p className="text-xs font-medium text-bad">{err}</p> : hint && <p className="text-xs text-muted">{hint}</p>}
      </div>
    );
  }

  if (def.value_type === 'choice') {
    return (
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium" htmlFor={`f-${def.key}`}>
          {loc(def.name_ar, def.name_en)} {def.unit && <span className="text-xs text-muted">({loc(def.unit, def.unit_en)})</span>}
        </label>
        <select id={`f-${def.key}`} className="field-input" {...register(`values.${def.key}.n`)}>
          <option value="">{tr.form.choose}</option>
          {def.choices?.map((c) => (
            <option key={c.value} value={c.value}>
              {loc(c.label, c.label_en)}
            </option>
          ))}
        </select>
        <input className="field-input py-2 text-xs" placeholder={tr.form.choiceNotes} {...register(`values.${def.key}.t`)} />
        {err ? <p className="text-xs font-medium text-bad">{err}</p> : hint && <p className="text-xs text-muted">{hint}</p>}
      </div>
    );
  }

  if (def.value_type === 'text') {
    return (
      <Textarea
        label={loc(def.name_ar, def.name_en)}
        wrapperClassName="sm:col-span-2"
        placeholder={previous?.display || tr.form.textPlaceholder}
        rows={3}
        {...register(`values.${def.key}.t`)}
      />
    );
  }

  return (
    <Input
      label={loc(def.name_ar, def.name_en)}
      type="number"
      step="any"
      inputMode="decimal"
      dir="ltr"
      placeholder={prevText ?? ''}
      suffix={loc(def.unit, def.unit_en) || undefined}
      error={err}
      hint={hint}
      {...register(`values.${def.key}.n`)}
    />
  );
}

function Section({
  category,
  defs,
  open,
  onToggle,
  control,
  children,
}: {
  category: Category;
  defs: Definition[];
  open: boolean;
  onToggle: () => void;
  control: Control<FormValues>;
  children: ReactNode;
}) {
  const values = useWatch({ control, name: 'values' });
  const filled = defs.filter((d) => isFilled(d, values?.[d.key])).length;
  return (
    <Card className="overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-4 py-3.5 text-start transition hover:bg-surface-2/60 sm:px-5"
      >
        <span className="text-primary">{categoryIcon[category]}</span>
        <span className="flex-1 font-bold">{tr.categories[category]}</span>
        <span className="num text-xs text-muted">
          {filled}/{defs.length} {tr.form.filled}
        </span>
        <ChevronDown className={clsx('h-5 w-5 text-muted transition', open && 'rotate-180')} />
      </button>
      <div className={clsx('grid gap-4 border-t border-line p-4 sm:grid-cols-2 sm:p-5', !open && 'hidden')}>{children}</div>
    </Card>
  );
}

export function SessionForm({
  clientId,
  session,
  onDone,
  onCancel,
}: {
  clientId: number;
  session?: Session | null;
  onDone?: (s: SessionDetail) => void;
  onCancel?: () => void;
}) {
  const defsQ = useDefinitions();
  const summary = useSummary(clientId);
  if (defsQ.isLoading) return <Skeleton className="h-96" />;
  if (defsQ.error || !defsQ.data) return <ErrorState message={errorMessage(defsQ.error)} onRetry={() => defsQ.refetch()} />;
  return (
    <SessionFormInner
      key={session?.id ?? 'new'}
      clientId={clientId}
      defs={defsQ.data}
      session={session}
      previous={summary.data?.latest_values ?? []}
      onDone={onDone}
      onCancel={onCancel}
    />
  );
}

function SessionFormInner({
  clientId,
  defs,
  session,
  previous,
  onDone,
  onCancel,
}: {
  clientId: number;
  defs: Definition[];
  session?: Session | null;
  previous: SummaryValue[];
  onDone?: (s: SessionDetail) => void;
  onCancel?: () => void;
}) {
  const schema = useMemo(() => buildSchema(defs), [defs]);
  const invalidate = useInvalidateClient();
  const [openCats, setOpenCats] = useState<Record<Category, boolean>>({ vital: true, body: true, movement: true, physical: true });
  const prevMap = useMemo(() => Object.fromEntries(previous.map((p) => [p.key, p])), [previous]);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: initialValues(defs, session) });

  const save = useMutation({
    mutationFn: (data: FormValues) => {
      const body = { session_date: data.session_date, notes: data.notes.trim() || null, values: toPayload(defs, data) };
      return session ? sessionsApi.update(session.id, body) : clientsApi.createSession(clientId, body);
    },
    onSuccess: async (s) => {
      toast.success(session ? tr.form.updated : tr.form.created);
      await invalidate(clientId);
      onDone?.(s);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const onInvalid = (errs: FieldErrors<FormValues>) => {
    // Open any section that contains an error so the message is visible.
    const bad = Object.keys(errs.values ?? {});
    setOpenCats((prev) => {
      const next = { ...prev };
      defs.filter((d) => bad.includes(d.key)).forEach((d) => (next[d.category] = true));
      return next;
    });
  };

  const allOpen = CATEGORIES.every((c) => openCats[c]);

  return (
    <form onSubmit={handleSubmit((d) => save.mutate(d), onInvalid)} className="flex flex-col gap-4" noValidate>
      <Card className="grid gap-4 p-4 sm:grid-cols-[14rem_1fr] sm:p-5">
        <Input
          type="date"
          label={tr.form.sessionDate}
          max={todayISO()}
          required
          error={errors.session_date?.message}
          {...register('session_date')}
        />
        <Textarea label={tr.form.sessionNotes} rows={2} {...register('notes')} />
        <p className="text-xs text-muted sm:col-span-2">{tr.form.allOptional}</p>
      </Card>

      <div className="flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setOpenCats({ vital: !allOpen, body: !allOpen, movement: !allOpen, physical: !allOpen })}
        >
          {allOpen ? tr.form.collapseAll : tr.form.expandAll}
        </Button>
      </div>

      {CATEGORIES.map((cat) => {
        const catDefs = defs.filter((d) => d.category === cat && d.is_active);
        if (!catDefs.length) return null;
        return (
          <Section
            key={cat}
            category={cat}
            defs={catDefs}
            open={openCats[cat]}
            onToggle={() => setOpenCats((p) => ({ ...p, [cat]: !p[cat] }))}
            control={control}
          >
            {catDefs.map((d) => (
              <FieldInput key={d.key} def={d} previous={prevMap[d.key]} register={register} errors={errors} />
            ))}
          </Section>
        );
      })}

      <div className="sticky bottom-[calc(4.75rem+env(safe-area-inset-bottom))] z-10 flex gap-2 rounded-2xl border border-line bg-surface/95 p-3 shadow-lg backdrop-blur md:bottom-4">
        <Button type="submit" size="lg" loading={save.isPending} icon={<Save className="h-5 w-5" />} className="flex-1 sm:flex-none">
          {session ? tr.form.submitEdit : tr.form.submitNew}
        </Button>
        {onCancel && (
          <Button variant="secondary" size="lg" onClick={onCancel}>
            {tr.common.cancel}
          </Button>
        )}
      </div>
    </form>
  );
}
