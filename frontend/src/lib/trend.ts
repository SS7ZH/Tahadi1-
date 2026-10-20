import type { Direction, Trend } from '@/api/types';

/** Mirrors backend services/progress.trend. */
export function trendOf(direction: Direction, change: number | null | undefined): Trend {
  if (change === null || change === undefined || Math.abs(change) < 1e-9 || direction === 'none') return 'neutral';
  return (change < 0 && direction === 'down') || (change > 0 && direction === 'up') ? 'good' : 'bad';
}
