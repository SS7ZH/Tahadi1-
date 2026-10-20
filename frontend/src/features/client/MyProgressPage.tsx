import { ProgressPanel } from '@/components/ProgressPanel';
import { SummaryView } from '@/components/SummaryView';
import { PageHeader } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { ar } from '@/i18n/ar';

/** Read-only: no edit/delete buttons and no new-measurement form for players. */
export function MyProgressPage() {
  const user = useCurrentUser();
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={`${ar.nav.myProgress} 💪`}
        subtitle={user.trainer_name ? `${ar.client.trainer}: ${user.trainer_name}` : undefined}
      />
      <SummaryView clientId={user.id} audience="client" />
      <ProgressPanel clientId={user.id} />
    </div>
  );
}
