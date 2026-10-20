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
import { ar } from '@/i18n/ar';
import { fmtDate, fmtNumber } from '@/lib/format';

const infoSchema = z.object({
  full_name: z.string().trim().min(2, ar.common.required).max(120),
  phone: z.string().trim().max(30).optional(),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(1, ar.profile.currentRequired),
    new_password: z.string().min(8, ar.profile.passwordMin),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, { path: ['confirm'], message: ar.profile.passwordMismatch });

export function ProfilePage() {
  const user = useCurrentUser();
  const { setUser } = useAuth();
  const factors = useActivityFactors();

  const info = useForm<z.infer<typeof infoSchema>>({
    resolver: zodResolver(infoSchema),
    defaultValues: { full_name: user.full_name, phone: user.phone ?? '' },
  });
  const pwd = useForm<z.infer<typeof passwordSchema>>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: '', new_password: '', confirm: '' },
  });

  const saveInfo = useMutation({
    mutationFn: authApi.updateMe,
    onSuccess: (u) => {
      setUser(u);
      toast.success(ar.profile.updated);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const savePwd = useMutation({
    mutationFn: authApi.updateMe,
    onSuccess: () => {
      pwd.reset();
      toast.success(ar.profile.passwordUpdated);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const p = user.profile;
  const activity = factors.data?.find((f) => f.key === p?.activity_key);

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={ar.profile.title} subtitle={`${ar.roles[user.role]} · ${user.email}`} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title={ar.profile.personal} icon={<UserRound className="h-5 w-5" />} />
          <form
            className="flex flex-col gap-4 p-4 sm:p-5"
            onSubmit={info.handleSubmit((v) => saveInfo.mutate({ full_name: v.full_name, phone: v.phone ?? '' }))}
          >
            <Input label={ar.profile.fullName} error={info.formState.errors.full_name?.message} {...info.register('full_name')} />
            <Input label={ar.profile.phone} type="tel" dir="ltr" inputMode="tel" {...info.register('phone')} />
            <Button type="submit" loading={saveInfo.isPending} className="self-start">
              {ar.common.save}
            </Button>
          </form>
        </Card>

        <Card>
          <CardHeader title={ar.profile.changePassword} icon={<KeyRound className="h-5 w-5" />} />
          <form
            className="flex flex-col gap-4 p-4 sm:p-5"
            onSubmit={pwd.handleSubmit((v) =>
              savePwd.mutate({ current_password: v.current_password, new_password: v.new_password }),
            )}
          >
            <Input
              label={ar.profile.currentPassword}
              type="password"
              autoComplete="current-password"
              dir="ltr"
              error={pwd.formState.errors.current_password?.message}
              {...pwd.register('current_password')}
            />
            <Input
              label={ar.profile.newPassword}
              type="password"
              autoComplete="new-password"
              dir="ltr"
              error={pwd.formState.errors.new_password?.message}
              {...pwd.register('new_password')}
            />
            <Input
              label={ar.profile.confirmPassword}
              type="password"
              autoComplete="new-password"
              dir="ltr"
              error={pwd.formState.errors.confirm?.message}
              {...pwd.register('confirm')}
            />
            <Button type="submit" loading={savePwd.isPending} className="self-start">
              {ar.profile.changePassword}
            </Button>
          </form>
        </Card>

        {user.role === 'client' && p && (
          <Card className="lg:col-span-2">
            <CardHeader
              title={ar.profile.trainerManaged}
              subtitle={ar.profile.trainerManagedHint}
              icon={<Lock className="h-5 w-5" />}
            />
            <dl className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3 sm:p-5">
              <Info label={ar.profile.trainer} value={user.trainer_name ?? ar.profile.noTrainer} />
              <Info label={ar.client.sex} value={ar.sex[p.sex]} />
              <Info label={ar.client.birthDate} value={fmtDate(p.birth_date)} />
              <Info label={ar.client.age} value={user.age != null ? `${user.age} ${ar.common.years}` : '—'} />
              <Info label={ar.client.height} value={<span className="num">{fmtNumber(p.height_cm)}</span>} />
              <Info label={ar.client.goal} value={ar.goals[p.goal]} />
              <Info label={ar.client.activity} value={activity?.name_ar ?? '—'} />
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
