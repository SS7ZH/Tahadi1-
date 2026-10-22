import { ClipboardList } from 'lucide-react';
import { errorMessage } from '@/api/client';
import { ProgramView } from '@/components/ProgramView';
import { Card, EmptyState, ErrorState, PageHeader, Skeleton } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { useCurrentProgram } from '@/hooks/queries';
import { tr } from '@/i18n';

/** Read-only: the player's active program, today's workout first. The PDF button is inside ProgramView. */
export function MyProgramPage() {
  const user = useCurrentUser();
  const { data, isLoading, error, refetch } = useCurrentProgram(user.id);
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={tr.nav.myProgram} subtitle={user.trainer_name ? `${tr.client.trainer}: ${user.trainer_name}` : undefined} />
      {isLoading ? (
        <Skeleton className="h-96" />
      ) : error ? (
        <ErrorState message={errorMessage(error)} onRetry={() => refetch()} />
      ) : !data ? (
        <Card>
          <EmptyState icon={<ClipboardList className="h-6 w-6" />} title={tr.program.empty} description={tr.program.emptyClient} />
        </Card>
      ) : (
        <ProgramView program={data} askHref={(dayId) => `/me/ask?day=${dayId}`} />
      )}
    </div>
  );
}
