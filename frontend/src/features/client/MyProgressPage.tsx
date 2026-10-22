import { FileDown } from 'lucide-react';
import { useState } from 'react';
import { ExportMeasurementsModal } from '@/components/ExportMeasurementsModal';
import { ProgressPanel } from '@/components/ProgressPanel';
import { SummaryView } from '@/components/SummaryView';
import { Button, PageHeader } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { tr } from '@/i18n';

/** Read-only: no edit/delete buttons and no new-measurement form for players. */
export function MyProgressPage() {
  const user = useCurrentUser();
  const [exportOpen, setExportOpen] = useState(false);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={`${tr.nav.myProgress} 💪`}
        subtitle={user.trainer_name ? `${tr.client.trainer}: ${user.trainer_name}` : undefined}
        actions={
          <Button
            variant="outline"
            size="sm"
            icon={<FileDown className="h-4 w-4" />}
            onClick={() => setExportOpen(true)}
          >
            {tr.pdf.exportPdf}
          </Button>
        }
      />
      <SummaryView clientId={user.id} audience="client" />
      <ProgressPanel clientId={user.id} />
      <ExportMeasurementsModal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        clientId={user.id}
      />
    </div>
  );
}
