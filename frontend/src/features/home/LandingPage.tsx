import clsx from 'clsx';
import { Activity, Calculator, Check, ClipboardList, Copy, FileText, Mail, MessageCircle, MessageCircleQuestion, Phone, Ruler, Salad } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { HomeContent, Plan } from '@/api/types';
import { LogoMark } from '@/components/Logo';
import { PublicShell } from '@/components/PublicShell';
import { Button, Card, Skeleton } from '@/components/ui';
import { homePathFor, useAuth } from '@/hooks/useAuth';
import { usePublicPlans, usePublicSite } from '@/hooks/queries';
import { loc, tr } from '@/i18n';

const FEATURE_ICONS: Record<string, ReactNode> = {
  measurements: <Ruler className="h-6 w-6" />,
  programs: <ClipboardList className="h-6 w-6" />,
  nutrition: <Salad className="h-6 w-6" />,
  reports: <FileText className="h-6 w-6" />,
  questions: <MessageCircleQuestion className="h-6 w-6" />,
};

function CopyRow({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked: the value is still visible to select */
    }
  };
  return (
    <li className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-3">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted">{label}</p>
        <p className="num truncate font-semibold" dir="ltr">
          {value}
        </p>
      </div>
      <Button size="sm" variant="outline" onClick={copy} icon={copied ? <Check className="h-4 w-4 text-good" /> : <Copy className="h-4 w-4" />}>
        {copied ? tr.landing.copied : tr.landing.copy}
      </Button>
    </li>
  );
}

function PlanCard({ p, highlight }: { p: Plan; highlight: boolean }) {
  return (
    <Card className={clsx('flex flex-col gap-2 p-5', highlight && 'border-primary ring-2 ring-primary/20')}>
      <p className="text-lg font-bold">{loc(p.name_ar, p.name_en)}</p>
      <p className="text-2xl font-bold text-primary">
        {p.price != null ? (
          <>
            <span className="num">{p.price.toLocaleString('en-US')}</span> <span className="text-sm font-semibold text-muted">{p.currency}</span>
          </>
        ) : (
          <span className="text-base">{tr.landing.priceOnRequest}</span>
        )}
      </p>
    </Card>
  );
}

function Hero({ home }: { home: HomeContent | undefined }) {
  const { user } = useAuth();
  return (
    <section className="relative overflow-hidden bg-[#141416] text-white">
      <div aria-hidden className="absolute -start-24 -top-24 h-80 w-80 rounded-full bg-primary/40 blur-3xl" />
      <div aria-hidden className="absolute -bottom-32 end-0 h-72 w-72 rounded-full bg-accent/30 blur-3xl" />
      <div className="relative mx-auto grid max-w-6xl items-center gap-8 px-4 py-14 sm:py-20 md:grid-cols-[1.3fr_1fr]">
        <div>
          {home ? (
            <>
              <h1 className="text-3xl font-bold leading-tight sm:text-5xl">{loc(home.hero_title_ar, home.hero_title_en)}</h1>
              <p className="mt-4 max-w-xl text-base leading-relaxed text-white/75 sm:text-lg">{loc(home.hero_text_ar, home.hero_text_en)}</p>
            </>
          ) : (
            <>
              <Skeleton className="h-12 w-3/4 bg-white/10" />
              <Skeleton className="mt-4 h-16 w-full bg-white/10" />
            </>
          )}
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to={user ? homePathFor(user.role) : '/login'}>
              <Button size="lg">{user ? tr.landing.myDashboard : tr.landing.login}</Button>
            </Link>
            <Link to="/calculator">
              <Button size="lg" variant="outline" icon={<Calculator className="h-5 w-5" />} className="border-white/30 bg-white/10 text-white hover:bg-white/20">
                {tr.landing.tryCalculator}
              </Button>
            </Link>
          </div>
          <p className="mt-4 text-xs text-white/50">{tr.landing.noSignup}</p>
        </div>
        <div className="hidden justify-center md:flex" aria-hidden>
          <div className="relative">
            <LogoMark className="h-48 w-48 drop-shadow-2xl" />
            <span className="absolute -end-6 -top-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10 text-primary backdrop-blur">
              <Activity className="h-7 w-7" />
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

export function LandingPage() {
  const site = usePublicSite();
  const plans = usePublicPlans();
  const home = site.data?.home;
  const contact = home?.contact;
  const hasContact = !!(contact && (contact.phone || contact.whatsapp || contact.email));

  useEffect(() => {
    document.title = `${tr.brand} · ${home ? loc(home.hero_title_ar, home.hero_title_en) : tr.tagline}`;
  }, [home]);

  return (
    <PublicShell>
      <Hero home={home} />

      <section id="features" className="mx-auto max-w-6xl scroll-mt-16 px-4 py-14">
        <h2 className="mb-6 text-2xl font-bold">{tr.landing.featuresTitle}</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(home?.features ?? []).map((f) => (
            <Card key={f.key} className="flex flex-col gap-3 p-5">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">{FEATURE_ICONS[f.key]}</span>
              <h3 className="text-lg font-bold">{loc(f.title_ar, f.title_en)}</h3>
              <p className="text-sm leading-relaxed text-muted">{loc(f.text_ar, f.text_en)}</p>
            </Card>
          ))}
          {!home && [0, 1, 2].map((i) => <Skeleton key={i} className="h-40" />)}
        </div>
      </section>

      <section id="how" className="scroll-mt-16 border-y border-line bg-surface">
        <div className="mx-auto max-w-6xl px-4 py-14">
          <h2 className="mb-6 text-2xl font-bold">{tr.landing.howTitle}</h2>
          <ol className="grid gap-4 md:grid-cols-3">
            {tr.landing.steps.map((s, i) => (
              <li key={s.title} className="flex gap-4 rounded-2xl border border-line bg-bg p-5">
                <span className="num flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-lg font-bold text-on-primary">{i + 1}</span>
                <div>
                  <h3 className="font-bold">{s.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{s.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="plans" className="mx-auto max-w-6xl scroll-mt-16 px-4 py-14">
        <h2 className="text-2xl font-bold">{tr.landing.plansTitle}</h2>
        <p className="mb-6 mt-1 text-sm text-muted">{tr.landing.plansText}</p>
        {plans.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-28" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {(plans.data ?? []).map((p, i, all) => (
              <PlanCard key={p.id} p={p} highlight={i === Math.min(1, all.length - 1)} />
            ))}
          </div>
        )}
      </section>

      <section id="contact" className="scroll-mt-16 border-t border-line bg-surface">
        <div className="mx-auto max-w-6xl px-4 py-14">
          <h2 className="mb-6 text-2xl font-bold">{tr.landing.contactTitle}</h2>
          {hasContact ? (
            <ul className="grid gap-3 md:grid-cols-3">
              {contact!.phone && <CopyRow icon={<Phone className="h-5 w-5" />} label={tr.landing.phone} value={contact!.phone} />}
              {contact!.whatsapp && <CopyRow icon={<MessageCircle className="h-5 w-5" />} label={tr.landing.whatsapp} value={contact!.whatsapp} />}
              {contact!.email && <CopyRow icon={<Mail className="h-5 w-5" />} label={tr.landing.email} value={contact!.email} />}
            </ul>
          ) : (
            <p className="text-sm text-muted">{tr.landing.noContact}</p>
          )}
        </div>
      </section>
    </PublicShell>
  );
}
