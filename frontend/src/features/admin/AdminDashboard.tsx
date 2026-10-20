import { Activity, CalendarCheck, Dumbbell, MessageCircleQuestion, UserX, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { errorMessage } from '@/api/client';
import { Card, CardHeader, EmptyState, ErrorState, PageHeader, Skeleton, SkeletonCards, StatCard } from '@/components/ui';
import { useAdminStats } from '@/hooks/queries';
import { ar } from '@/i18n/ar';
import { fmtDateTime } from '@/lib/format';

export function AdminDashboard() {
  const { data, isLoading, error, refetch } = useAdminStats();

  return (
    <div>
      <PageHeader title={ar.admin.dashboard} />
      {isLoading ? (
        <>
          <SkeletonCards count={5} className="lg:grid-cols-5" />
          <Skeleton className="mt-5 h-72" />
        </>
      ) : error || !data ? (
        <ErrorState message={errorMessage(error)} onRetry={() => refetch()} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
            <Link to="/admin/users?role=trainer">
              <StatCard label={ar.admin.trainers} value={<span className="num">{data.trainers}</span>} icon={<Dumbbell className="h-4 w-4" />} />
            </Link>
            <Link to="/admin/users?role=client">
              <StatCard label={ar.admin.clients} value={<span className="num">{data.clients}</span>} icon={<Users className="h-4 w-4" />} tone="accent" />
            </Link>
            <StatCard
              label={ar.admin.measurementsMonth}
              value={<span className="num">{data.measurements_this_month}</span>}
              icon={<CalendarCheck className="h-4 w-4" />}
              tone="good"
            />
            <Link to="/admin/questions">
              <StatCard
                label={ar.admin.openQuestions}
                value={<span className="num">{data.open_questions}</span>}
                icon={<MessageCircleQuestion className="h-4 w-4" />}
                tone={data.open_questions ? 'warn' : 'neutral'}
              />
            </Link>
            <Link to="/admin/assign">
              <StatCard
                label={ar.admin.unassigned}
                value={<span className="num">{data.unassigned_clients}</span>}
                icon={<UserX className="h-4 w-4" />}
                tone={data.unassigned_clients ? 'bad' : 'neutral'}
              />
            </Link>
          </div>

          <Card className="mt-5">
            <CardHeader title={ar.admin.recentActivity} icon={<Activity className="h-5 w-5" />} />
            {data.recent_activity.length === 0 ? (
              <EmptyState title={ar.admin.noActivity} />
            ) : (
              <ul className="divide-y divide-line">
                {data.recent_activity.map((a) => (
                  <li key={a.id} className="flex items-center justify-between gap-3 px-4 py-3 sm:px-5">
                    <p className="text-sm">
                      <b>{a.actor_name ?? '—'}</b> {ar.admin.actions[a.action] ?? a.action}{' '}
                      {ar.admin.entities[a.entity] ?? a.entity}
                      {a.client_name && <span className="text-muted"> — {a.client_name}</span>}
                    </p>
                    <span className="shrink-0 text-[11px] text-muted">{fmtDateTime(a.timestamp)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
