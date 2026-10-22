import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarClock, FileText, HeartPulse } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { onboardingApi } from '@/api/endpoints';
import type { HealthInput, MedicalFileInfo, SignedDocumentInfo } from '@/api/types';
import { DeclarationView, emptyHealth, HealthForm, SignedDocList, SignedDocModal } from '@/components/documents';
import { Badge, Button, Card, CardHeader, Modal, PageHeader, Skeleton } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { useDocuments, useHealth, useSubscriptions } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { fmtDate } from '@/lib/format';

function UpdateHealthModal({ open, onClose, initial }: { open: boolean; onClose: () => void; initial: HealthInput }) {
  const user = useCurrentUser();
  const qc = useQueryClient();
  const [value, setValue] = useState<HealthInput>(initial);
  const [files, setFiles] = useState<MedicalFileInfo[]>([]);
  const save = useMutation({
    mutationFn: () => onboardingApi.updateHealth({ ...value, file_ids: files.map((f) => f.id) }),
    onSuccess: async () => {
      toast.success(tr.documents.healthUpdated);
      await qc.invalidateQueries({ queryKey: ['client', user.id] });
      onClose();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const invalid = value.has_chronic && (!value.conditions.length || !(value.details ?? '').trim());
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={tr.documents.updateHealth}
      size="lg"
      footer={
        <Button loading={save.isPending} disabled={invalid} onClick={() => save.mutate()}>
          {tr.common.save}
        </Button>
      }
    >
      <HealthForm
        value={value}
        onChange={setValue}
        files={files}
        onUpload={async (f) => {
          try {
            const up = await onboardingApi.uploadFile(f, true);
            setFiles((xs) => [...xs, up]);
            toast.success(tr.onboarding.uploaded);
          } catch (e) {
            toast.error(errorMessage(e));
          }
        }}
      />
    </Modal>
  );
}

export function MyDocumentsPage() {
  const user = useCurrentUser();
  const subs = useSubscriptions(user.id);
  const health = useHealth(user.id);
  const docs = useDocuments(user.id);
  const [open, setOpen] = useState<SignedDocumentInfo | null>(null);
  const [editing, setEditing] = useState(false);
  const sub = subs.data?.current;
  const current = health.data?.current;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <PageHeader title={tr.documents.title} />

      <Card>
        <CardHeader title={tr.documents.subscription} icon={<CalendarClock className="h-5 w-5" />} />
        <div className="p-4 sm:p-5">
          {subs.isLoading ? (
            <Skeleton className="h-16" />
          ) : sub ? (
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex-1">
                <p className="font-bold">{loc(sub.plan_name_ar, sub.plan_name_en)}</p>
                <p className="text-sm text-muted">
                  {fmtDate(sub.start_date)} – {fmtDate(sub.end_date)}
                </p>
              </div>
              <Badge tone={sub.status === 'expired' ? 'bad' : sub.status === 'upcoming' ? 'warn' : 'good'}>
                {sub.status === 'active' ? tr.documents.daysLeft(Math.max(0, sub.days_left ?? 0)) : tr.subscriptionStatus[sub.status ?? 'active']}
              </Badge>
            </div>
          ) : null}
        </div>
      </Card>

      <Card>
        <CardHeader
          title={tr.documents.health}
          icon={<HeartPulse className="h-5 w-5" />}
          actions={
            <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
              {tr.documents.updateHealth}
            </Button>
          }
        />
        <div className="p-4 sm:p-5">
          {health.isLoading ? <Skeleton className="h-20" /> : current ? <DeclarationView d={current} /> : <p className="text-sm text-muted">{tr.documents.noHealth}</p>}
        </div>
      </Card>

      <Card>
        <CardHeader title={tr.documents.signedDocs} icon={<FileText className="h-5 w-5" />} />
        {docs.isLoading ? <Skeleton className="m-5 h-20" /> : <SignedDocList docs={docs.data ?? []} onOpen={setOpen} />}
      </Card>

      <SignedDocModal doc={open} onClose={() => setOpen(null)} />
      {editing && (
        <UpdateHealthModal
          open
          onClose={() => setEditing(false)}
          initial={
            current
              ? { has_chronic: current.has_chronic, conditions: current.conditions, details: current.details ?? '', medications: current.medications ?? '', injuries: current.injuries ?? '', file_ids: [] }
              : emptyHealth()
          }
        />
      )}
    </div>
  );
}
