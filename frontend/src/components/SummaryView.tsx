import clsx from 'clsx';
import { Activity, CalendarDays, Flame, Gauge, HeartPulse, Ruler, Scale } from 'lucide-react';
import type { ReactNode } from 'react';
import { errorMessage } from '@/api/client';
import { CATEGORIES, type Results, type SummaryValue } from '@/api/types';
import { useSummary } from '@/hooks/queries';
import { ar } from '@/i18n/ar';
import { fmtDate, fmtInt, fmtNumber } from '@/lib/format';
import { TrendChip } from './TrendChip';
import { Badge, Card, CardHeader, EmptyState, ErrorState, Skeleton, SkeletonCards } from './ui';

const categoryIcon: Record<string, ReactNode> = {
  vital: <HeartPulse className="h-5 w-5" />,
  body: <Ruler className="h-5 w-5" />,
  movement: <Activity className="h-5 w-5" />,
  physical: <Gauge className="h-5 w-5" />,
};

function riskTone(key: string | undefined): 'good' | 'warn' | 'bad' | 'neutral' {
  if (!key) return 'neutral';
  if (['normal'].includes(key)) return 'good';
  if (['elevated', 'overweight', 'underweight', 'stage1'].includes(key)) return 'warn';
  return 'bad';
}

export function ResultCards({ results, bmiChange, bmiTrend }: { results: Results; bmiChange?: number | null; bmiTrend?: SummaryValue['trend'] }) {
  const cards: { label: string; icon: ReactNode; value: ReactNode; sub: ReactNode; badge?: ReactNode }[] = [
    {
      label: ar.summary.bmi,
      icon: <Scale className="h-4 w-4" />,
      value: results.bmi ? <span className="num">{fmtNumber(results.bmi.value, 1)}</span> : '—',
      sub: results.bmi ? null : ar.summary.missingForCalc,
      badge: results.bmi && (
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge tone={riskTone(results.bmi.category)}>{results.bmi.label}</Badge>
          {bmiTrend && <TrendChip change={bmiChange} trend={bmiTrend} />}
        </div>
      ),
    },
    {
      label: ar.summary.whr,
      icon: <Ruler className="h-4 w-4" />,
      value: results.whr ? <span className="num">{fmtNumber(results.whr.value)}</span> : '—',
      sub: results.whr ? `${ar.summary.risk}:` : null,
      badge: results.whr && <Badge tone={riskTone(results.whr.risk)}>{results.whr.label}</Badge>,
    },
    {
      label: ar.summary.bmr,
      icon: <Flame className="h-4 w-4" />,
      value: results.bmr ? <span className="num">{fmtInt(results.bmr)}</span> : '—',
      sub: results.bmr ? ar.common.kcalPerDay : ar.summary.missingForCalc,
    },
    {
      label: ar.summary.tdee,
      icon: <Activity className="h-4 w-4" />,
      value: results.tdee ? <span className="num">{fmtInt(results.tdee)}</span> : '—',
      sub: results.activity ? (
        <span>
          {ar.common.kcalPerDay} · {results.activity.name_ar} (<span className="num">×{results.activity.factor}</span>)
        </span>
      ) : (
        ar.summary.missingForCalc
      ),
    },
    {
      label: ar.summary.bp,
      icon: <HeartPulse className="h-4 w-4" />,
      value: results.blood_pressure ? (
        <span className="num">
          {results.blood_pressure.systolic}/{results.blood_pressure.diastolic}
        </span>
      ) : (
        '—'
      ),
      sub: results.blood_pressure ? 'mmHg' : null,
      badge: results.blood_pressure && (
        <Badge tone={riskTone(results.blood_pressure.category)}>{results.blood_pressure.label}</Badge>
      ),
    },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
      {cards.map((c, i) => (
        <Card key={c.label} className={clsx('flex flex-col gap-2 p-4', i === 0 && 'col-span-2 md:col-span-1')}>
          <div className="flex items-center justify-between gap-2 text-xs font-medium text-muted">
            <span>{c.label}</span>
            <span className="text-primary">{c.icon}</span>
          </div>
          <div className="text-2xl font-bold leading-none">{c.value}</div>
          {c.sub && <div className="text-xs text-muted">{c.sub}</div>}
          {c.badge}
        </Card>
      ))}
    </div>
  );
}

function ValueRow({ v }: { v: SummaryValue }) {
  const isText = v.value_type === 'text';
  return (
    <li className="flex items-start justify-between gap-3 py-2.5">
      <div className="min-w-0">
        <p className="text-sm font-medium">{v.name_ar}</p>
        <p className="text-[11px] text-muted">{fmtDate(v.session_date)}</p>
        {isText && <p className="mt-1 text-sm leading-relaxed text-ink/80">{v.display}</p>}
        {v.value_type === 'choice' && v.value_text && <p className="mt-1 text-xs text-muted">{v.value_text}</p>}
      </div>
      {!isText && (
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className="font-bold">
            <span className={v.value_type === 'choice' ? '' : 'num'}>{v.display}</span>
            {v.unit && v.value_type !== 'choice' && <span className="ms-1 text-xs font-normal text-muted">{v.unit}</span>}
          </span>
          <TrendChip change={v.change} trend={v.trend} />
        </div>
      )}
    </li>
  );
}

export function SummaryView({ clientId, audience }: { clientId: number; audience: 'staff' | 'client' }) {
  const { data, isLoading, error, refetch } = useSummary(clientId);

  if (isLoading)
    return (
      <div className="flex flex-col gap-4">
        <SkeletonCards count={5} className="lg:grid-cols-5" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  if (error) return <ErrorState message={errorMessage(error)} onRetry={() => refetch()} />;
  if (!data) return null;

  if (data.sessions_count === 0)
    return (
      <Card>
        <EmptyState
          icon={<CalendarDays className="h-6 w-6" />}
          title={ar.summary.noData}
          description={audience === 'staff' ? ar.summary.noDataTrainer : ar.summary.noDataClient}
        />
      </Card>
    );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-muted">
        <span>
          {ar.summary.sessions}: <b className="num text-ink">{data.sessions_count}</b>
        </span>
        <span>
          {ar.summary.firstSession}: <b className="text-ink">{fmtDate(data.first_session_date)}</b>
        </span>
        <span>
          {ar.summary.lastSession}: <b className="text-ink">{fmtDate(data.last_session_date)}</b>
        </span>
      </div>

      <ResultCards results={data.results} bmiChange={data.bmi_change} bmiTrend={data.bmi_trend} />
      {data.results.targets && (
        <p className="text-xs text-muted">
          {ar.calculator.targets}: {ar.calculator.maintenance} <b className="num">{data.results.targets.maintenance}</b> ·{' '}
          {ar.calculator.fatLoss} <b className="num">{data.results.targets.fat_loss}</b> · {ar.calculator.muscleGain}{' '}
          <b className="num">{data.results.targets.muscle_gain}</b> {ar.common.kcal} — {ar.calculator.targetsNote}
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {CATEGORIES.map((cat) => {
          const items = data.latest_values.filter((v) => v.category === cat);
          if (!items.length) return null;
          return (
            <Card key={cat}>
              <CardHeader title={ar.categories[cat]} icon={categoryIcon[cat]} subtitle={ar.common.changeSinceStart} />
              <ul className="divide-y divide-line px-4 sm:px-5">
                {items.map((v) => (
                  <ValueRow key={v.key} v={v} />
                ))}
              </ul>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
