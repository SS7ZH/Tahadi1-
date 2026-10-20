import { Inbox } from 'lucide-react';
import { useState } from 'react';
import { errorMessage } from '@/api/client';
import type { QuestionStatus } from '@/api/types';
import { QuestionCard } from '@/components/QuestionThread';
import { Card, EmptyState, ErrorState, PageHeader, Skeleton, Tabs } from '@/components/ui';
import { useInbox } from '@/hooks/queries';
import { ar } from '@/i18n/ar';

type Filter = QuestionStatus | 'all';

export function InboxPage() {
  const [filter, setFilter] = useState<Filter>('open');
  const { data, isLoading, error, refetch } = useInbox(filter === 'all' ? '' : filter);
  const openCount = useInbox('open').data?.length ?? 0;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={ar.questions.inboxTitle} />
      <div className="mb-4">
        <Tabs<Filter>
          value={filter}
          onChange={setFilter}
          items={[
            { value: 'open', label: ar.questionStatus.open, badge: openCount },
            { value: 'answered', label: ar.questionStatus.answered },
            { value: 'closed', label: ar.questionStatus.closed },
            { value: 'all', label: ar.common.all },
          ]}
        />
      </div>
      {isLoading ? (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      ) : error ? (
        <ErrorState message={errorMessage(error)} onRetry={() => refetch()} />
      ) : !data?.length ? (
        <Card>
          <EmptyState icon={<Inbox className="h-6 w-6" />} title={ar.questions.inboxEmpty} description={ar.questions.inboxEmptyHint} />
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {data.map((q) => (
            <QuestionCard key={q.id} question={q} showClient />
          ))}
        </div>
      )}
    </div>
  );
}
