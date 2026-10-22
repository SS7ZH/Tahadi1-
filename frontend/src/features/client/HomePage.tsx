import clsx from 'clsx';
import { CalendarClock, ChevronLeft, ClipboardList, MessageSquare, Salad } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { MacroSplitChart } from '@/components/MacroView';
import { dayFor } from '@/components/ProgramView';
import { Badge, Card, Skeleton } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { useComments, useCurrentProgram, useNutrition, useSubscriptions } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { fmtDate, fmtDateTime, fmtInt } from '@/lib/format';

function Tile({ title, icon, to, linkLabel, children }: { title: string; icon: ReactNode; to?: string; linkLabel?: string; children: ReactNode }) {
  return (
    <Card className="flex flex-col p-4">
      <div className="mb-3 flex items-center gap-2">
        <span className="text-primary">{icon}</span>
        <h2 className="font-bold">{title}</h2>
        {to && (
          <Link to={to} className="ms-auto inline-flex items-center gap-0.5 text-xs font-semibold text-primary hover:underline">
            {linkLabel}
            <ChevronLeft className="h-3.5 w-3.5 ltr:rotate-180" />
          </Link>
        )}
      </div>
      {children}
    </Card>
  );
}

/** Player home: subscription days left, today's workout, calories & macros, latest coach comment. */
export function HomePage() {
  const user = useCurrentUser();
  const subs = useSubscriptions(user.id);
  const program = useCurrentProgram(user.id);
  const nutrition = useNutrition(user.id);
  const comments = useComments(user.id);
  const sub = subs.data?.current;
  const plan = nutrition.data?.current;
  const p = program.data;
  const today = p?.today;
  const todayDay = today?.day_id ? p?.days.find((d) => d.id === today.day_id) : today?.week && today.day_number && p ? dayFor(p, today.week, today.day_number) : undefined;
  const latest = comments.data?.[0];

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-bold sm:text-2xl">{tr.home.hello(user.full_name.split(' ')[0])}</h1>

      {subs.isLoading ? (
        <Skeleton className="h-20" />
      ) : sub ? (
        <Card className={clsx('flex flex-wrap items-center gap-3 p-4', sub.status === 'expired' && 'border-bad/40 bg-bad/5')}>
          <CalendarClock className={clsx('h-6 w-6', sub.status === 'expired' ? 'text-bad' : 'text-primary')} />
          <div className="flex-1">
            <p className="font-bold">
              {sub.status === 'expired'
                ? tr.subscriptionStatus.expired
                : sub.status === 'upcoming'
                  ? tr.documents.upcoming
                  : tr.documents.daysLeft(Math.max(0, sub.days_left ?? 0))}
            </p>
            <p className="text-xs text-muted">
              {loc(sub.plan_name_ar, sub.plan_name_en)} · {fmtDate(sub.start_date)} – {fmtDate(sub.end_date)}
            </p>
          </div>
          <Badge tone={sub.status === 'expired' ? 'bad' : sub.status === 'upcoming' ? 'warn' : 'good'}>{tr.subscriptionStatus[sub.status ?? 'active']}</Badge>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <Tile title={tr.home.todayWorkout} icon={<ClipboardList className="h-5 w-5" />} to="/me/program" linkLabel={tr.home.openProgram}>
          {program.isLoading ? (
            <Skeleton className="h-24" />
          ) : !p ? (
            <p className="text-sm text-muted">{tr.home.noProgram}</p>
          ) : today?.state === 'finished' ? (
            <p className="text-sm text-muted">{tr.program.finished}</p>
          ) : todayDay && !todayDay.is_rest && today?.state === 'running' ? (
            <div>
              <p className="font-semibold">{todayDay.title}</p>
              <p className="text-xs text-muted">{tr.home.exercises(todayDay.items.length)}</p>
              <ul className="mt-2 flex flex-col gap-1 text-sm">
                {todayDay.items.slice(0, 5).map((it) => (
                  <li key={it.id} className="truncate">
                    • {it.kind === 'cardio' ? tr.cardioTypes[it.cardio_type ?? ''] : loc(it.exercise_name_ar, it.exercise_name_en) || it.custom_name}
                    {it.kind === 'resistance' && it.sets && it.reps && <span className="num ms-1 text-muted">{tr.program.setsReps(it.sets, it.reps)}</span>}
                  </li>
                ))}
              </ul>
            </div>
          ) : today?.state === 'not_started' ? (
            <p className="text-sm text-muted">{tr.program.notStarted(today.starts_in_days ?? 0)}</p>
          ) : (
            <p className="text-sm font-semibold">{tr.program.todayRest}</p>
          )}
        </Tile>

        <Tile title={tr.home.todayCalories} icon={<Salad className="h-5 w-5" />} to="/me/nutrition" linkLabel={tr.home.openNutrition}>
          {nutrition.isLoading ? (
            <Skeleton className="h-24" />
          ) : !plan ? (
            <p className="text-sm text-muted">{tr.home.noNutrition}</p>
          ) : (
            <div className="flex items-center gap-4">
              <MacroSplitChart numbers={plan} size={120} />
              <ul className="flex flex-col gap-1 text-sm">
                {(['protein', 'carbs', 'fat'] as const).map((m) => (
                  <li key={m}>
                    {tr.macros[m]}: <b className="num">{fmtInt(plan.grams[m])}</b>
                    {tr.nutrition.grams}
                  </li>
                ))}
                <li className="text-xs text-muted">
                  {tr.nutrition.mealsPerDay}: <span className="num">{plan.meals_per_day}</span>
                </li>
              </ul>
            </div>
          )}
        </Tile>
      </div>

      <Tile title={tr.home.latestComment} icon={<MessageSquare className="h-5 w-5" />} to="/me/history" linkLabel={tr.nav.myHistory}>
        {comments.isLoading ? (
          <Skeleton className="h-16" />
        ) : latest ? (
          <div className="rounded-xl border-s-4 border-primary bg-primary/5 px-3 py-2">
            <p className="whitespace-pre-line text-sm">{latest.body}</p>
            <p className="mt-1 text-[11px] text-muted">
              {latest.author_name} · {fmtDateTime(latest.created_at)}
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted">{tr.home.noComment}</p>
        )}
      </Tile>
    </div>
  );
}
