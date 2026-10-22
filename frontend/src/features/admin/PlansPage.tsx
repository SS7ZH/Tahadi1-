import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';
import { Plus, Power, Save } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { documentsApi } from '@/api/endpoints';
import type { Plan } from '@/api/types';
import { Button, Card, ErrorState, IconButton, Input, PageHeader, Skeleton } from '@/components/ui';
import { tr } from '@/i18n';

type Form = { name_ar: string; name_en: string; months: string; price: string; currency: string };
const toForm = (p?: Plan): Form => ({
  name_ar: p?.name_ar ?? '',
  name_en: p?.name_en ?? '',
  months: String(p?.months ?? 1),
  price: p?.price != null ? String(p.price) : '',
  currency: p?.currency ?? 'SAR',
});

function PlanRow({ plan, onSaved }: { plan?: Plan; onSaved: () => void }) {
  const [f, setF] = useState<Form>(toForm(plan));
  const set = (k: keyof Form, v: string) => setF((s) => ({ ...s, [k]: v }));
  const save = useMutation({
    mutationFn: () => {
      const body = { name_ar: f.name_ar.trim(), name_en: f.name_en.trim(), months: Number(f.months), currency: f.currency.trim().toUpperCase() };
      const price = f.price.trim() === '' ? null : Number(f.price);
      if (plan) return documentsApi.updatePlan(plan.id, price == null ? { ...body, clear_price: true } : { ...body, price });
      return documentsApi.createPlan({ ...body, price });
    },
    onSuccess: () => {
      toast.success(tr.plansAdmin.saved);
      if (!plan) setF(toForm());
      onSaved();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const toggle = useMutation({
    mutationFn: () => documentsApi.updatePlan(plan!.id, { is_active: !plan!.is_active }),
    onSuccess: onSaved,
    onError: (e) => toast.error(errorMessage(e)),
  });
  const valid = f.name_ar.trim() && f.name_en.trim() && Number(f.months) >= 1 && f.currency.trim().length === 3;
  return (
    <li className={clsx('grid gap-2 px-4 py-3 sm:grid-cols-2 sm:px-5 lg:grid-cols-[1fr_1fr_6rem_7rem_5rem_auto] lg:items-end', plan && !plan.is_active && 'opacity-50')}>
      <Input label={tr.admin.nameAr} value={f.name_ar} onChange={(e) => set('name_ar', e.target.value)} />
      <Input label={tr.admin.nameEn} dir="ltr" value={f.name_en} onChange={(e) => set('name_en', e.target.value)} />
      <Input label={tr.plansAdmin.months} type="number" dir="ltr" value={f.months} onChange={(e) => set('months', e.target.value)} />
      <Input label={tr.plansAdmin.price} type="number" dir="ltr" value={f.price} onChange={(e) => set('price', e.target.value)} />
      <Input label={tr.plansAdmin.currency} dir="ltr" value={f.currency} onChange={(e) => set('currency', e.target.value)} />
      <div className="flex gap-1">
        <Button disabled={!valid} loading={save.isPending} onClick={() => save.mutate()} icon={plan ? <Save className="h-4 w-4" /> : <Plus className="h-4 w-4" />}>
          {plan ? tr.common.save : tr.common.add}
        </Button>
        {plan && (
          <IconButton label={plan.is_active ? tr.admin.deactivate : tr.admin.activate} onClick={() => toggle.mutate()}>
            <Power className="h-4 w-4" />
          </IconButton>
        )}
      </div>
    </li>
  );
}

export function PlansPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['admin', 'plans'], queryFn: documentsApi.adminPlans });
  const refresh = () => Promise.all([qc.invalidateQueries({ queryKey: ['admin', 'plans'] }), qc.invalidateQueries({ queryKey: ['plans'] })]);
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title={tr.plansAdmin.title} />
      {q.isLoading ? (
        <Skeleton className="h-64" />
      ) : q.error ? (
        <ErrorState message={errorMessage(q.error)} onRetry={() => q.refetch()} />
      ) : (
        <Card className="overflow-hidden">
          <ul className="divide-y divide-line">
            {q.data?.map((p) => (
              <PlanRow key={`${p.id}-${p.is_active}-${p.price}-${p.name_ar}`} plan={p} onSaved={refresh} />
            ))}
            <li className="bg-surface-2/40 px-4 pt-3 text-sm font-bold sm:px-5">{tr.plansAdmin.newPlan}</li>
            <PlanRow onSaved={refresh} />
          </ul>
        </Card>
      )}
    </div>
  );
}
