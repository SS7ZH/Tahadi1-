import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { z } from 'zod';
import { errorMessage } from '@/api/client';
import { clientsApi } from '@/api/endpoints';
import type { User } from '@/api/types';
import { Button, Input, Modal, Select, Textarea } from '@/components/ui';
import { useActivityFactors } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { todayISO } from '@/lib/format';

const makeBase = () => ({
  full_name: z.string().trim().min(2, tr.common.required).max(120),
  phone: z.string().trim().max(30).optional(),
  sex: z.enum(['male', 'female']),
  birth_date: z.string().min(1, tr.common.required).refine((v) => v < todayISO(), tr.common.required),
  height_cm: z.coerce.number({ invalid_type_error: tr.client.heightRange }).min(100, tr.client.heightRange).max(250, tr.client.heightRange),
  goal: z.enum(['fat_loss', 'muscle_gain', 'fitness', 'health', 'performance']),
  activity_key: z.string().min(1),
  notes: z.string().max(5000).optional(),
});
const makeCreateSchema = () =>
  z.object({
    ...makeBase(),
    email: z.string().trim().email(tr.auth.invalidEmail),
    password: z.string().min(8, tr.profile.passwordMin),
  });
const makeEditSchema = () => z.object(makeBase());
type CreateValues = z.infer<ReturnType<typeof makeCreateSchema>>;

export function ClientFormModal({ open, onClose, client }: { open: boolean; onClose: () => void; client?: User | null }) {
  const qc = useQueryClient();
  const factors = useActivityFactors();
  const editing = !!client;
  const p = client?.profile;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateValues>({
    resolver: zodResolver(editing ? (makeEditSchema() as unknown as ReturnType<typeof makeCreateSchema>) : makeCreateSchema()),
    values: {
      full_name: client?.full_name ?? '',
      phone: client?.phone ?? '',
      email: client?.email ?? '',
      password: '',
      sex: p?.sex ?? 'male',
      birth_date: p?.birth_date ?? '',
      height_cm: p?.height_cm ?? ('' as unknown as number),
      goal: p?.goal ?? 'fitness',
      activity_key: p?.activity_key ?? 'moderate',
      notes: p?.notes ?? '',
    },
  });

  const save = useMutation({
    mutationFn: (v: CreateValues) => {
      const body = {
        full_name: v.full_name,
        phone: v.phone || null,
        sex: v.sex,
        birth_date: v.birth_date,
        height_cm: Number(v.height_cm),
        goal: v.goal,
        activity_key: v.activity_key,
        notes: v.notes || null,
      };
      return editing ? clientsApi.update(client!.id, body) : clientsApi.create({ ...body, email: v.email, password: v.password });
    },
    onSuccess: async () => {
      toast.success(editing ? tr.common.saved : tr.client.created);
      await Promise.all([qc.invalidateQueries({ queryKey: ['clients'] }), qc.invalidateQueries({ queryKey: ['client'] })]);
      reset();
      onClose();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editing ? tr.client.editClient : tr.client.newClient}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {tr.common.cancel}
          </Button>
          <Button type="submit" form="client-form" loading={save.isPending}>
            {editing ? tr.common.save : tr.common.create}
          </Button>
        </>
      }
    >
      <form id="client-form" onSubmit={handleSubmit((v) => save.mutate(v))} className="grid gap-4 sm:grid-cols-2" noValidate>
        <Input label={tr.client.fullName} error={errors.full_name?.message} {...register('full_name')} />
        <Input label={tr.client.phone} type="tel" dir="ltr" {...register('phone')} />
        {!editing && (
          <>
            <Input label={tr.client.email} type="email" dir="ltr" autoComplete="off" error={errors.email?.message} {...register('email')} />
            <Input
              label={tr.client.password}
              type="password"
              dir="ltr"
              autoComplete="new-password"
              error={errors.password?.message}
              {...register('password')}
            />
          </>
        )}
        <Select label={tr.client.sex} {...register('sex')}>
          <option value="male">{tr.sex.male}</option>
          <option value="female">{tr.sex.female}</option>
        </Select>
        <Input label={tr.client.birthDate} type="date" max={todayISO()} error={errors.birth_date?.message} {...register('birth_date')} />
        <Input
          label={tr.client.height}
          type="number"
          step="any"
          inputMode="decimal"
          dir="ltr"
          error={errors.height_cm?.message}
          {...register('height_cm')}
        />
        <Select label={tr.client.goal} {...register('goal')}>
          {Object.entries(tr.goals).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </Select>
        <Select label={tr.client.activity} wrapperClassName="sm:col-span-2" {...register('activity_key')}>
          {factors.data?.map((f) => (
            <option key={f.key} value={f.key}>
              {loc(f.name_ar, f.name_en)} — {loc(f.description_ar, f.description_en)} (×{f.factor})
            </option>
          ))}
        </Select>
        <Textarea label={tr.client.notes} wrapperClassName="sm:col-span-2" rows={2} {...register('notes')} />
      </form>
    </Modal>
  );
}
