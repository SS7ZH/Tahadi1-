import { CalendarCheck, CalendarClock, ChevronLeft, MessageCircleQuestion, Plus, Search, Send, Users } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { errorMessage } from '@/api/client';
import type { ClientListItem } from '@/api/types';
import { TrendChip } from '@/components/TrendChip';
import { Badge, Button, Card, CardHeader, CountBadge, EmptyState, ErrorState, Input, PageHeader, Skeleton, StatCard } from '@/components/ui';
import { useClients } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { daysAgo, fmtNumber, relativeDays } from '@/lib/format';
import { ChronicBadge } from '@/components/documents';
import { ClientFormModal } from './ClientFormModal';
import { TelegramPlayerModal } from './telegram/TelegramPlayerModal';

export function ClientRow({ c, href }: { c: ClientListItem; href: string }) {
  const stale = (daysAgo(c.last_session_date) ?? 999) > 30;
  return (
    <Link to={href} className="block">
      <Card className="flex items-center gap-3 p-3.5 transition hover:border-primary/40 hover:shadow-md sm:p-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent/15 text-base font-bold text-accent">
          {c.full_name.charAt(0)}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate font-bold">{c.full_name}</p>
            {!c.is_active && <Badge tone="bad">{tr.common.inactive}</Badge>}
            {c.goal && <Badge>{tr.goals[c.goal]}</Badge>}
            {c.has_chronic && <ChronicBadge />}
            {c.health_update_pending && <Badge tone="warn">{tr.documents.updatedBadge}</Badge>}
            {c.subscription_status === 'expired' && <Badge tone="bad">{tr.subscriptionStatus.expired}</Badge>}
            {c.telegram_linked ? (
              <Badge tone="good"><Send className="h-3 w-3" /> {loc('تيليجرام', 'Telegram')}</Badge>
            ) : (
              !c.email && <Badge tone="warn">{loc('بانتظار ربط المجموعة', 'Group not linked')}</Badge>
            )}
          </div>
          <p className={`mt-0.5 text-xs ${stale ? 'text-warn' : 'text-muted'}`}>
            {tr.client.lastSession}: {c.last_session_date ? relativeDays(c.last_session_date) : tr.client.noSessions}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {c.weight_latest !== null && (
            <span className="text-sm font-bold">
              <span className="num">{fmtNumber(c.weight_latest)}</span> <span className="text-xs font-normal text-muted">{tr.common.kg}</span>
            </span>
          )}
          <TrendChip change={c.weight_change} trend={c.weight_trend} />
        </div>
        {c.open_questions > 0 && (
          <span title={tr.client.openQuestions} className="flex items-center gap-1 text-primary">
            <MessageCircleQuestion className="h-4 w-4" />
            <CountBadge count={c.open_questions} />
          </span>
        )}
        <ChevronLeft className="h-5 w-5 shrink-0 text-muted ltr:rotate-180" />
      </Card>
    </Link>
  );
}

export function TrainerDashboard() {
  const { data, isLoading, error, refetch } = useClients();
  const [q, setQ] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [showTelegram, setShowTelegram] = useState(false);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    return (data ?? []).filter((c) => !s || c.full_name.toLowerCase().includes(s) || (c.email ?? "").toLowerCase().includes(s));
  }, [data, q]);

  const expiring = useMemo(
    () =>
      (data ?? [])
        .filter((c) => c.subscription_status === 'active' && c.subscription_days_left != null && c.subscription_days_left <= 7)
        .sort((x, y) => (x.subscription_days_left ?? 0) - (y.subscription_days_left ?? 0)),
    [data],
  );

  const stats = useMemo(() => {
    const list = data ?? [];
    return {
      clients: list.length,
      open: list.reduce((n, c) => n + c.open_questions, 0),
      recent: list.filter((c) => (daysAgo(c.last_session_date) ?? 999) <= 30).length,
    };
  }, [data]);

  return (
    <div>
      <PageHeader
        title={tr.trainer.title}
        subtitle={tr.trainer.subtitle}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button icon={<Send className="h-4 w-4" />} onClick={() => setShowTelegram(true)}>
              {loc('لاعب جديد (تيليجرام)', 'New player (Telegram)')}
            </Button>
            <Button variant="outline" icon={<Plus className="h-4 w-4" />} onClick={() => setShowNew(true)}>
              {loc('حساب بدخول للموقع', 'Account with web login')}
            </Button>
          </div>
        }
      />

      <div className="mb-5 grid grid-cols-3 gap-3">
        <StatCard label={tr.trainer.clients} value={<span className="num">{isLoading ? '…' : stats.clients}</span>} icon={<Users className="h-4 w-4" />} />
        <Link to="/trainer/questions">
          <StatCard
            label={tr.trainer.unanswered}
            value={<span className="num">{isLoading ? '…' : stats.open}</span>}
            icon={<MessageCircleQuestion className="h-4 w-4" />}
            tone={stats.open ? 'warn' : 'neutral'}
          />
        </Link>
        <StatCard
          label={tr.trainer.measuredThisMonth}
          value={<span className="num">{isLoading ? '…' : stats.recent}</span>}
          icon={<CalendarCheck className="h-4 w-4" />}
          tone="good"
        />
      </div>

      {expiring.length > 0 && (
        <Card className="mb-5 border-warn/40">
          <CardHeader title={tr.documents.expiringSoon} icon={<CalendarClock className="h-5 w-5" />} />
          <ul className="divide-y divide-line">
            {expiring.map((c) => (
              <li key={c.id}>
                <Link to={`/trainer/clients/${c.id}?tab=documents`} className="flex items-center justify-between gap-2 px-4 py-2.5 text-sm hover:bg-surface-2 sm:px-5">
                  <span className="font-semibold">{c.full_name}</span>
                  <Badge tone="warn">{tr.documents.daysLeft(c.subscription_days_left ?? 0)}</Badge>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="mb-4 max-w-md">
        <Input
          aria-label={tr.common.search}
          placeholder={tr.common.search}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          suffix={<Search className="h-4 w-4" />}
        />
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-[4.5rem]" />
          ))}
        </div>
      ) : error ? (
        <ErrorState message={errorMessage(error)} onRetry={() => refetch()} />
      ) : !data?.length ? (
        <Card>
          <EmptyState
            icon={<Users className="h-6 w-6" />}
            title={tr.trainer.empty}
            description={tr.trainer.emptyHint}
            action={
              <Button icon={<Send className="h-4 w-4" />} onClick={() => setShowTelegram(true)}>
                {loc('لاعب جديد (تيليجرام)', 'New player (Telegram)')}
              </Button>
            }
          />
        </Card>
      ) : filtered.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted">{tr.trainer.noResults}</p>
      ) : (
        <div className="flex flex-col gap-2.5">
          {filtered.map((c) => (
            <ClientRow key={c.id} c={c} href={`/trainer/clients/${c.id}`} />
          ))}
        </div>
      )}

      <ClientFormModal open={showNew} onClose={() => setShowNew(false)} />
      <TelegramPlayerModal open={showTelegram} onClose={() => setShowTelegram(false)} />
    </div>
  );
}
