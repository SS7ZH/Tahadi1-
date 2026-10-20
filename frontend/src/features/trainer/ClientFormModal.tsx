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
import { ar } from '@/i18n/ar';
import { todayISO } from '@/lib/format';

const base = {
  full_name: z.string().trim().min(2, ar.common.required).max(120),
  phone: z.string().trim().max(30).optional(),
  sex: z.enum(['male', 'female']),
  birth_date: z.string().min(1, ar.common.required).refine((v) => v < todayISO(), ar.common.required),
  height_cm: z.coerce.number({ invalid_type_error: ar.client.heightRange }).min(100, ar.client.heightRange).max(250, ar.client.heightRange),
  goal: z.enum(['fat_loss', 'muscle_gain', 'fitness', 'health']),
  activity_key: z.string().min(1),
  notes: z.string().max(5000).optional(),
};
const createSchema = z.object({
  ...base,
  email: z.string().trim().email(ar.auth.invalidEmail),
  password: z.string().min(8, ar.profile.passwordMin),
});
const editSchema = z.object(base);
type CreateValues = z.infer<typeof createSchema>;

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
    resolver: zodResolver(editing ? (editSchema as unknown as typeof createSchema) : createSchema),
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
      toast.success(editing ? ar.common.saved : ar.client.created);
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
      title={editing ? ar.client.editClient : ar.client.newClient}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {ar.common.cancel}
          </Button>
          <Button type="submit" form="client-form" loading={save.isPending}>
            {editing ? ar.common.save : ar.common.create}
          </Button>
        </>
      }
    >
      <form id="client-form" onSubmit={handleSubmit((v) => save.mutate(v))} className="grid gap-4 sm:grid-cols-2" noValidate>
        <Input label={ar.client.fullName} error={errors.full_name?.message} {...register('full_name')} />
        <Input label={ar.client.phone} type="tel" dir="ltr" {...register('phone')} />
        {!editing && (
          <>
            <Input label={ar.client.email} type="email" dir="ltr" autoComplete="off" error={errors.email?.message} {...register('email')} />
            <Input
              label={ar.client.password}
              type="password"
              dir="ltr"
              autoComplete="new-password"
              error={errors.password?.message}
              {...register('password')}
            />
          </>
        )}
        <Select label={ar.client.sex} {...register('sex')}>
          <option value="male">{ar.sex.male}</option>
          <option value="female">{ar.sex.female}</option>
        </Select>
        <Input label={ar.client.birthDate} type="date" max={todayISO()} error={errors.birth_date?.message} {...register('birth_date')} />
        <Input
          label={ar.client.height}
          type="number"
          step="any"
          inputMode="decimal"
          dir="ltr"
          error={errors.height_cm?.message}
          {...register('height_cm')}
        />
        <Select label={ar.client.goal} {...register('goal')}>
          {Object.entries(ar.goals).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </Select>
        <Select label={ar.client.activity} wrapperClassName="sm:col-span-2" {...register('activity_key')}>
          {factors.data?.map((f) => (
            <option key={f.key} value={f.key}>
              {f.name_ar} — {f.description_ar} (×{f.factor})
            </option>
          ))}
        </Select>
        <Textarea label={ar.client.notes} wrapperClassName="sm:col-span-2" rows={2} {...register('notes')} />
      </form>
    </Modal>
  );
}
