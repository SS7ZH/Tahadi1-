import { ProgressPanel } from '@/components/ProgressPanel';
import { SummaryView } from '@/components/SummaryView';
import { PageHeader } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { tr } from '@/i18n';

/** Read-only: no edit/delete buttons and no new-measurement form for players.
 *  The measurements PDF export lives in ProgressPanel (same button for coaches and players). */
export function MyProgressPage() {
  const user = useCurrentUser();
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={`${tr.nav.myProgress} 💪`}
        subtitle={user.trainer_name ? `${tr.client.trainer}: ${user.trainer_name}` : undefined}
      />
      <SummaryView clientId={user.id} audience="client" />
      <ProgressPanel clientId={user.id} />
    </div>
  );
}
