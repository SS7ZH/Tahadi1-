import { CommentThread } from '@/components/CommentThread';
import { SessionHistory } from '@/components/SessionHistory';
import { PageHeader } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { tr } from '@/i18n';

export function MyHistoryPage() {
  const user = useCurrentUser();
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={tr.nav.myHistory} />
      <SessionHistory clientId={user.id} canEdit={false} />
      <section>
        <h2 className="mb-3 text-lg font-bold">{tr.comments.title}</h2>
        <CommentThread clientId={user.id} canWrite={false} />
      </section>
    </div>
  );
}
