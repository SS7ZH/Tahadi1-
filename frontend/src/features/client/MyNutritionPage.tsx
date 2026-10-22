import { Salad } from 'lucide-react';
import { errorMessage } from '@/api/client';
import { MacroView } from '@/components/MacroView';
import { Badge, Card, EmptyState, ErrorState, PageHeader, Skeleton } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { useNutrition } from '@/hooks/queries';
import { tr } from '@/i18n';
import { fmtDate, fmtInt } from '@/lib/format';

/** Read-only: the plan the coach saved. */
export function MyNutritionPage() {
  const user = useCurrentUser();
  const { data, isLoading, error, refetch } = useNutrition(user.id);
  const plan = data?.current;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={tr.nav.myNutrition} subtitle={user.trainer_name ? `${tr.client.trainer}: ${user.trainer_name}` : undefined} />
      {isLoading ? (
        <Skeleton className="h-80" />
      ) : error ? (
        <ErrorState message={errorMessage(error)} onRetry={() => refetch()} />
      ) : !plan ? (
        <Card>
          <EmptyState icon={<Salad className="h-6 w-6" />} title={tr.nutrition.clientEmpty} description={tr.nutrition.clientEmptyHint} />
        </Card>
      ) : (
        <Card className="p-4 sm:p-6">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
            <div>
              <p className="text-sm text-muted">{tr.nutrition.calories}</p>
              <p className="text-3xl font-bold">
                <span className="num">{fmtInt(plan.calories)}</span>{' '}
                <span className="text-base font-normal text-muted">{tr.common.kcalPerDay}</span>
              </p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <Badge tone="primary">{tr.nutritionGoals[plan.nutrition_goal]}</Badge>
              <span className="text-[11px] text-muted">
                {tr.nutrition.updatedBy}: {fmtDate(plan.created_at.slice(0, 10))}
              </span>
            </div>
          </div>
          <MacroView numbers={plan} />
          {plan.note && <p className="mt-4 rounded-xl border-s-4 border-primary bg-primary/5 px-3 py-2 text-sm">{plan.note}</p>}
          <p className="mt-4 text-xs text-muted">{tr.calculator.targetsNote}</p>
        </Card>
      )}
    </div>
  );
}
