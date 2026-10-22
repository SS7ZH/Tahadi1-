import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, useWatch } from 'react-hook-form';
import { toast } from 'sonner';
import { z } from 'zod';
import { errorMessage } from '@/api/client';
import { adminApi, type AdminUserBody } from '@/api/endpoints';
import type { Role, User } from '@/api/types';
import { Button, Input, Modal, Select, Textarea } from '@/components/ui';
import { useActivityFactors, useAdminUsers } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { todayISO } from '@/lib/format';

const makeSchema = () =>
  z
  .object({
    full_name: z.string().trim().min(2, tr.common.required).max(120),
    email: z.string().trim().email(tr.auth.invalidEmail),
    phone: z.string().trim().max(30).optional(),
    password: z.string(),
    role: z.enum(['admin', 'trainer', 'client']),
    sex: z.enum(['male', 'female']),
    birth_date: z.string(),
    height_cm: z.string(),
    goal: z.enum(['fat_loss', 'muscle_gain', 'fitness', 'health', 'performance']),
    activity_key: z.string(),
    trainer_id: z.string(),
    notes: z.string().optional(),
    editing: z.boolean(),
  })
  .superRefine((v, ctx) => {
    if (!v.editing && v.password.length < 8) ctx.addIssue({ code: 'custom', path: ['password'], message: tr.profile.passwordMin });
    if (v.editing && v.password && v.password.length < 8)
      ctx.addIssue({ code: 'custom', path: ['password'], message: tr.profile.passwordMin });
    if (v.role === 'client') {
      if (!v.birth_date) ctx.addIssue({ code: 'custom', path: ['birth_date'], message: tr.common.required });
      const h = Number(v.height_cm);
      if (!v.height_cm || Number.isNaN(h) || h < 100 || h > 250)
        ctx.addIssue({ code: 'custom', path: ['height_cm'], message: tr.client.heightRange });
    }
  });
type Values = z.infer<ReturnType<typeof makeSchema>>;

export function UserFormModal({ open, onClose, user, defaultRole }: { open: boolean; onClose: () => void; user?: User | null; defaultRole?: Role }) {
  const qc = useQueryClient();
  const factors = useActivityFactors();
  const trainers = useAdminUsers('trainer');
  const editing = !!user;
  const p = user?.profile;

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(makeSchema()),
    values: {
      full_name: user?.full_name ?? '',
      email: user?.email ?? '',
      phone: user?.phone ?? '',
      password: '',
      role: user?.role ?? defaultRole ?? 'client',
      sex: p?.sex ?? 'male',
      birth_date: p?.birth_date ?? '',
      height_cm: p?.height_cm ? String(p.height_cm) : '',
      goal: p?.goal ?? 'fitness',
      activity_key: p?.activity_key ?? 'moderate',
      trainer_id: p?.trainer_id ? String(p.trainer_id) : '',
      notes: p?.notes ?? '',
      editing,
    },
  });
  const role = useWatch({ control, name: 'role' });

  const save = useMutation({
    mutationFn: (v: Values) => {
      const body: AdminUserBody = { full_name: v.full_name, email: v.email, phone: v.phone || null };
      if (v.password) body.password = v.password;
      if (v.role === 'client') {
        Object.assign(body, {
          sex: v.sex,
          birth_date: v.birth_date,
          height_cm: Number(v.height_cm),
          goal: v.goal,
          activity_key: v.activity_key,
          notes: v.notes || null,
        });
      }
      if (editing) return adminApi.updateUser(user!.id, body);
      return adminApi.createUser({ ...body, role: v.role, trainer_id: v.role === 'client' && v.trainer_id ? Number(v.trainer_id) : null });
    },
    onSuccess: async () => {
      toast.success(editing ? tr.admin.userUpdated : tr.admin.userCreated);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['admin'] }),
        qc.invalidateQueries({ queryKey: ['clients'] }),
        qc.invalidateQueries({ queryKey: ['client'] }),
      ]);
      onClose();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={editing ? tr.admin.editUser : tr.admin.newUser}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {tr.common.cancel}
          </Button>
          <Button type="submit" form="user-form" loading={save.isPending}>
            {editing ? tr.common.save : tr.common.create}
          </Button>
        </>
      }
    >
      <form id="user-form" className="grid gap-4 sm:grid-cols-2" onSubmit={handleSubmit((v) => save.mutate(v))} noValidate>
        <Select label={tr.admin.role} disabled={editing} {...register('role')}>
          {(['client', 'trainer', 'admin'] as Role[]).map((r) => (
            <option key={r} value={r}>
              {tr.roles[r]}
            </option>
          ))}
        </Select>
        <Input label={tr.client.fullName} error={errors.full_name?.message} {...register('full_name')} />
        <Input label={tr.client.email} type="email" dir="ltr" autoComplete="off" error={errors.email?.message} {...register('email')} />
        <Input label={tr.client.phone} type="tel" dir="ltr" {...register('phone')} />
        <Input
          label={editing ? tr.admin.newPasswordOptional : tr.client.password}
          type="password"
          dir="ltr"
          autoComplete="new-password"
          error={errors.password?.message}
          wrapperClassName="sm:col-span-2"
          {...register('password')}
        />

        {role === 'client' && (
          <>
            {!editing && (
              <Select label={tr.client.trainer} {...register('trainer_id')}>
                <option value="">{tr.admin.noTrainer}</option>
                {trainers.data
                  ?.filter((t) => t.is_active)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.full_name}
                    </option>
                  ))}
              </Select>
            )}
            <Select label={tr.client.sex} {...register('sex')}>
              <option value="male">{tr.sex.male}</option>
              <option value="female">{tr.sex.female}</option>
            </Select>
            <Input label={tr.client.birthDate} type="date" max={todayISO()} error={errors.birth_date?.message} {...register('birth_date')} />
            <Input label={tr.client.height} type="number" step="any" dir="ltr" error={errors.height_cm?.message} {...register('height_cm')} />
            <Select label={tr.client.goal} {...register('goal')}>
              {Object.entries(tr.goals).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
            <Select label={tr.client.activity} {...register('activity_key')}>
              {factors.data?.map((f) => (
                <option key={f.key} value={f.key}>
                  {loc(f.name_ar, f.name_en)} (×{f.factor})
                </option>
              ))}
            </Select>
            <Textarea label={tr.client.notes} rows={2} wrapperClassName="sm:col-span-2" {...register('notes')} />
          </>
        )}
      </form>
    </Modal>
  );
}
