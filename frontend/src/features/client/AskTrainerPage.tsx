import { QuestionThread } from '@/components/QuestionThread';
import { PageHeader } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { ar } from '@/i18n/ar';

export function AskTrainerPage() {
  const user = useCurrentUser();
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={ar.nav.ask} subtitle={user.trainer_name ? `${ar.client.trainer}: ${user.trainer_name}` : undefined} />
      <QuestionThread clientId={user.id} mode="client" />
    </div>
  );
}
