import { useSearchParams } from 'react-router-dom';
import { QuestionThread } from '@/components/QuestionThread';
import { PageHeader } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { tr } from '@/i18n';

export function AskTrainerPage() {
  const user = useCurrentUser();
  // "Ask about this day" from My program links here with ?day=<program day id>
  const [params, setParams] = useSearchParams();
  const day = Number(params.get('day')) || null;
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={tr.nav.ask} subtitle={user.trainer_name ? `${tr.client.trainer}: ${user.trainer_name}` : undefined} />
      <QuestionThread clientId={user.id} mode="client" dayId={day} onClearDay={() => setParams({}, { replace: true })} />
    </div>
  );
}
