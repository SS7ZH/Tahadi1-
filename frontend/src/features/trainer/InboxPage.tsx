import { Inbox } from 'lucide-react';
import { useState } from 'react';
import { errorMessage } from '@/api/client';
import type { QuestionStatus } from '@/api/types';
import { QuestionCard } from '@/components/QuestionThread';
import { Card, EmptyState, ErrorState, PageHeader, Skeleton, Tabs } from '@/components/ui';
import { useInbox } from '@/hooks/queries';
import { tr } from '@/i18n';

type Filter = QuestionStatus | 'all';

export function InboxPage() {
  const [filter, setFilter] = useState<Filter>('open');
  const { data, isLoading, error, refetch } = useInbox(filter === 'all' ? '' : filter);
  const openCount = useInbox('open').data?.length ?? 0;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={tr.questions.inboxTitle} />
      <div className="mb-4">
        <Tabs<Filter>
          value={filter}
          onChange={setFilter}
          items={[
            { value: 'open', label: tr.questionStatus.open, badge: openCount },
            { value: 'answered', label: tr.questionStatus.answered },
            { value: 'closed', label: tr.questionStatus.closed },
            { value: 'all', label: tr.common.all },
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
          <EmptyState icon={<Inbox className="h-6 w-6" />} title={tr.questions.inboxEmpty} description={tr.questions.inboxEmptyHint} />
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
