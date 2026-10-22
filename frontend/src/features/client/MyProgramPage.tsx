import { ClipboardList, FileDown } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { ProgramView } from '@/components/ProgramView';
import { Button, Card, EmptyState, ErrorState, PageHeader, Skeleton } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { useCurrentProgram } from '@/hooks/queries';
import { tr } from '@/i18n';
import { downloadPdf } from '@/lib/download';

/** Read-only: the player's active program, today's workout first. */
export function MyProgramPage() {
  const user = useCurrentUser();
  const { data, isLoading, error, refetch } = useCurrentProgram(user.id);
  const [downloading, setDownloading] = useState(false);

  const handleExport = async () => {
    if (!data) return;
    setDownloading(true);
    try {
      await downloadPdf(`/pdf/program/${data.id}`);
      toast.success(tr.pdf.exported);
    } catch (err) {
      toast.error(errorMessage(err) || tr.pdf.exportFailed);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title={tr.nav.myProgram}
        subtitle={user.trainer_name ? `${tr.client.trainer}: ${user.trainer_name}` : undefined}
        actions={
          data ? (
            <Button
              variant="outline"
              size="sm"
              icon={<FileDown className="h-4 w-4" />}
              loading={downloading}
              onClick={handleExport}
            >
              {tr.pdf.exportPdf}
            </Button>
          ) : undefined
        }
      />
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
