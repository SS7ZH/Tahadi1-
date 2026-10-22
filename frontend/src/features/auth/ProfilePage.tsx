import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { KeyRound, Lock, UserRound } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { z } from 'zod';
import { errorMessage } from '@/api/client';
import { authApi } from '@/api/endpoints';
import { Button, Card, CardHeader, Input, PageHeader } from '@/components/ui';
import { useAuth, useCurrentUser } from '@/hooks/useAuth';
import { useActivityFactors } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { fmtDate, fmtNumber } from '@/lib/format';

const makeInfoSchema = () =>
  z.object({
  full_name: z.string().trim().min(2, tr.common.required).max(120),
  phone: z.string().trim().max(30).optional(),
});

const makePasswordSchema = () =>
  z
  .object({
    current_password: z.string().min(1, tr.profile.currentRequired),
    new_password: z.string().min(8, tr.profile.passwordMin),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, { path: ['confirm'], message: tr.profile.passwordMismatch });

export function ProfilePage() {
  const user = useCurrentUser();
  const { setUser } = useAuth();
  const factors = useActivityFactors();

  const info = useForm<z.infer<ReturnType<typeof makeInfoSchema>>>({
    resolver: zodResolver(makeInfoSchema()),
    defaultValues: { full_name: user.full_name, phone: user.phone ?? '' },
  });
  const pwd = useForm<z.infer<ReturnType<typeof makePasswordSchema>>>({
    resolver: zodResolver(makePasswordSchema()),
    defaultValues: { current_password: '', new_password: '', confirm: '' },
  });

  const saveInfo = useMutation({
    mutationFn: authApi.updateMe,
    onSuccess: (u) => {
      setUser(u);
      toast.success(tr.profile.updated);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const savePwd = useMutation({
    mutationFn: authApi.updateMe,
    onSuccess: () => {
      pwd.reset();
      toast.success(tr.profile.passwordUpdated);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const p = user.profile;
  const activity = factors.data?.find((f) => f.key === p?.activity_key);

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={tr.profile.title} subtitle={`${tr.roles[user.role]} · ${user.email}`} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title={tr.profile.personal} icon={<UserRound className="h-5 w-5" />} />
          <form
            className="flex flex-col gap-4 p-4 sm:p-5"
            onSubmit={info.handleSubmit((v) => saveInfo.mutate({ full_name: v.full_name, phone: v.phone ?? '' }))}
          >
            <Input label={tr.profile.fullName} error={info.formState.errors.full_name?.message} {...info.register('full_name')} />
            <Input label={tr.profile.phone} type="tel" dir="ltr" inputMode="tel" {...info.register('phone')} />
            <Button type="submit" loading={saveInfo.isPending} className="self-start">
              {tr.common.save}
            </Button>
          </form>
        </Card>

        <Card>
          <CardHeader title={tr.profile.changePassword} icon={<KeyRound className="h-5 w-5" />} />
          <form
            className="flex flex-col gap-4 p-4 sm:p-5"
            onSubmit={pwd.handleSubmit((v) =>
              savePwd.mutate({ current_password: v.current_password, new_password: v.new_password }),
            )}
          >
            <Input
              label={tr.profile.currentPassword}
              type="password"
              autoComplete="current-password"
              dir="ltr"
              error={pwd.formState.errors.current_password?.message}
              {...pwd.register('current_password')}
            />
            <Input
              label={tr.profile.newPassword}
              type="password"
              autoComplete="new-password"
              dir="ltr"
              error={pwd.formState.errors.new_password?.message}
              {...pwd.register('new_password')}
            />
            <Input
              label={tr.profile.confirmPassword}
              type="password"
              autoComplete="new-password"
              dir="ltr"
              error={pwd.formState.errors.confirm?.message}
              {...pwd.register('confirm')}
            />
            <Button type="submit" loading={savePwd.isPending} className="self-start">
              {tr.profile.changePassword}
            </Button>
          </form>
        </Card>

        {user.role === 'client' && p && (
          <Card className="lg:col-span-2">
            <CardHeader
              title={tr.profile.trainerManaged}
              subtitle={tr.profile.trainerManagedHint}
              icon={<Lock className="h-5 w-5" />}
            />
            <dl className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3 sm:p-5">
              <Info label={tr.profile.trainer} value={user.trainer_name ?? tr.profile.noTrainer} />
              <Info label={tr.client.sex} value={tr.sex[p.sex]} />
              <Info label={tr.client.birthDate} value={fmtDate(p.birth_date)} />
              <Info label={tr.client.age} value={user.age != null ? `${user.age} ${tr.common.years}` : '—'} />
              <Info label={tr.client.height} value={<span className="num">{fmtNumber(p.height_cm)}</span>} />
              <Info label={tr.client.goal} value={tr.goals[p.goal]} />
              <Info label={tr.client.activity} value={activity ? loc(activity.name_ar, activity.name_en) : '—'} />
            </dl>
          </Card>
        )}
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 font-semibold">{value}</dd>
    </div>
  );
}
