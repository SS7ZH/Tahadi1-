import clsx from 'clsx';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import type { Trend } from '@/api/types';
import { ar } from '@/i18n/ar';
import { fmtSigned } from '@/lib/format';

const trendClass: Record<Trend, string> = {
  good: 'bg-good/10 text-good',
  bad: 'bg-bad/10 text-bad',
  neutral: 'bg-surface-2 text-muted',
};

export const trendText: Record<Trend, string> = {
  good: 'text-good',
  bad: 'text-bad',
  neutral: 'text-muted',
};

/** Green = toward the goal, red = away from it, grey = no change. */
export function TrendChip({
  change,
  trend,
  unit,
  size = 'sm',
}: {
  change: number | null | undefined;
  trend: Trend;
  unit?: string | null;
  size?: 'sm' | 'md';
}) {
  if (change === null || change === undefined) return null;
  const Icon = Math.abs(change) < 1e-9 ? Minus : change > 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <span
      title={ar.trend[trend]}
      className={clsx(
        'inline-flex items-center gap-0.5 rounded-full font-semibold',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
        trendClass[trend],
      )}
    >
      <Icon className={size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'} aria-hidden />
      <span className="num">{fmtSigned(change)}</span>
      {unit && <span className="opacity-80">{unit}</span>}
      <span className="sr-only">{ar.trend[trend]}</span>
    </span>
  );
}
