import { zodResolver } from '@hookform/resolvers/zod';
import { Activity, HeartPulse, LineChart } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { z } from 'zod';
import { errorMessage } from '@/api/client';
import { LanguageSwitch } from '@/components/LanguageSwitch';
import { Logo } from '@/components/Logo';
import { Button, Card, Input } from '@/components/ui';
import { homePathFor, useAuth } from '@/hooks/useAuth';
import { tr } from '@/i18n';
import { FullScreenLoader } from '@/routes/RequireRole';

const makeSchema = () =>
  z.object({
  email: z.string().trim().email(tr.auth.invalidEmail),
  password: z.string().min(1, tr.auth.passwordRequired),
});
type FormValues = z.infer<ReturnType<typeof makeSchema>>;

const DEMO = [
  { role: 'admin', email: 'admin@tahadi.app', password: 'Admin@12345' },
  { role: 'trainer', email: 'trainer1@tahadi.app', password: 'Demo@12345' },
  { role: 'client', email: 'client1@tahadi.app', password: 'Demo@12345' },
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
  } = useForm<FormValues>({ resolver: zodResolver(makeSchema()), defaultValues: { email: '', password: '' } });

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
        <Link to="/" className="relative self-start" aria-label={tr.brand}>
          <Logo className="[&_span]:text-white" />
        </Link>
        <div className="relative max-w-md">
          <h1 className="text-4xl font-bold leading-tight">{tr.auth.heroTitle}</h1>
          <p className="mt-4 text-lg leading-relaxed text-white/70">{tr.auth.heroText}</p>
          <div className="mt-8 flex gap-3">
            {[HeartPulse, Activity, LineChart].map((Icon, i) => (
              <span key={i} className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10">
                <Icon className="h-6 w-6 text-primary" />
              </span>
            ))}
          </div>
        </div>
        <p className="relative text-sm text-white/50">{tr.tagline}</p>
      </div>

      {/* form */}
      <div className="relative flex items-center justify-center px-4 py-10">
        <LanguageSwitch className="absolute end-4 top-4" />
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Link to="/" className="inline-block" aria-label={tr.brand}>
              <Logo />
            </Link>
            <p className="mt-2 text-sm text-muted">{tr.tagline}</p>
          </div>
          <h2 className="text-2xl font-bold">{tr.auth.title}</h2>
          <p className="mt-1 text-sm text-muted">{tr.auth.subtitle}</p>

          <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4" noValidate>
            <Input
              label={tr.auth.email}
              type="email"
              autoComplete="email"
              inputMode="email"
              dir="ltr"
              className="text-start"
              error={errors.email?.message}
              {...register('email')}
            />
            <Input
              label={tr.auth.password}
              type="password"
              autoComplete="current-password"
              dir="ltr"
              error={errors.password?.message}
              {...register('password')}
            />
            <Button type="submit" size="lg" loading={isSubmitting} className="mt-2 w-full">
              {isSubmitting ? tr.auth.submitting : tr.auth.submit}
            </Button>
          </form>

          {import.meta.env.DEV && (
            <Card className="mt-8 p-4">
              <p className="mb-3 text-xs font-semibold text-muted">{tr.auth.demo}</p>
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
                    {tr.roles[d.role]}
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
