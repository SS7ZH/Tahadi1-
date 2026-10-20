import { zodResolver } from '@hookform/resolvers/zod';
import { Activity, HeartPulse, LineChart } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { z } from 'zod';
import { errorMessage } from '@/api/client';
import { Logo } from '@/components/Logo';
import { Button, Card, Input } from '@/components/ui';
import { homePathFor, useAuth } from '@/hooks/useAuth';
import { ar } from '@/i18n/ar';
import { FullScreenLoader } from '@/routes/RequireRole';

const schema = z.object({
  email: z.string().trim().email(ar.auth.invalidEmail),
  password: z.string().min(1, ar.auth.passwordRequired),
});
type FormValues = z.infer<typeof schema>;

const DEMO = [
  { label: 'مدير', email: 'admin@tahadi.app', password: 'Admin@12345' },
  { label: 'مدرب', email: 'trainer1@tahadi.app', password: 'Demo@12345' },
  { label: 'لاعب', email: 'client1@tahadi.app', password: 'Demo@12345' },
];

export function LoginPage() {
  const { user, status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { email: '', password: '' } });

  if (status === 'loading') return <FullScreenLoader />;
  if (user) return <Navigate to={homePathFor(user.role)} replace />;

  const onSubmit = handleSubmit(async (values) => {
    try {
      const u = await login(values.email, values.password);
      const target = from && from !== '/login' ? from : homePathFor(u.role);
      navigate(target, { replace: true });
    } catch (err) {
      toast.error(errorMessage(err));
    }
  });

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      {/* brand panel */}
      <div className="relative hidden overflow-hidden bg-[#141416] p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div
          aria-hidden
          className="absolute -start-24 -top-24 h-96 w-96 rounded-full bg-primary/40 blur-3xl"
        />
        <div aria-hidden className="absolute -bottom-32 end-0 h-80 w-80 rounded-full bg-accent/30 blur-3xl" />
        <Logo className="relative [&_span]:text-white" />
        <div className="relative max-w-md">
          <h1 className="text-4xl font-bold leading-tight">{ar.auth.heroTitle}</h1>
          <p className="mt-4 text-lg leading-relaxed text-white/70">{ar.auth.heroText}</p>
          <div className="mt-8 flex gap-3">
            {[HeartPulse, Activity, LineChart].map((Icon, i) => (
              <span key={i} className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10">
                <Icon className="h-6 w-6 text-primary" />
              </span>
            ))}
          </div>
        </div>
        <p className="relative text-sm text-white/50">{ar.tagline}</p>
      </div>

      {/* form */}
      <div className="flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Logo />
            <p className="mt-2 text-sm text-muted">{ar.tagline}</p>
          </div>
          <h2 className="text-2xl font-bold">{ar.auth.title}</h2>
          <p className="mt-1 text-sm text-muted">{ar.auth.subtitle}</p>

          <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4" noValidate>
            <Input
              label={ar.auth.email}
              type="email"
              autoComplete="email"
              inputMode="email"
              dir="ltr"
              className="text-start"
              error={errors.email?.message}
              {...register('email')}
            />
            <Input
              label={ar.auth.password}
              type="password"
              autoComplete="current-password"
              dir="ltr"
              error={errors.password?.message}
              {...register('password')}
            />
            <Button type="submit" size="lg" loading={isSubmitting} className="mt-2 w-full">
              {isSubmitting ? ar.auth.submitting : ar.auth.submit}
            </Button>
          </form>

          {import.meta.env.DEV && (
            <Card className="mt-8 p-4">
              <p className="mb-3 text-xs font-semibold text-muted">{ar.auth.demo}</p>
              <div className="flex flex-wrap gap-2">
                {DEMO.map((d) => (
                  <Button
                    key={d.email}
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setValue('email', d.email);
                      setValue('password', d.password);
                    }}
                  >
                    {d.label}
                  </Button>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
