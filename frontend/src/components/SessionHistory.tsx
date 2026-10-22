import { useMutation } from '@tanstack/react-query';
import clsx from 'clsx';
import { CalendarDays, ChevronDown, FileDown, MessageSquare, Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { sessionsApi } from '@/api/endpoints';
import { CATEGORIES, type Session } from '@/api/types';
import { useInvalidateClient, useSessionDetail, useSessions } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { downloadPdf } from '@/lib/download';
import { fmtDate, fmtDateTime } from '@/lib/format';
import { ResultCards } from './SummaryView';
import { Badge, Card, ConfirmDialog, EmptyState, ErrorState, IconButton, Skeleton, Spinner } from './ui';

function SessionBody({ sessionId }: { sessionId: number }) {
  const { data, isLoading, error } = useSessionDetail(sessionId);
  if (isLoading)
    return (
      <div className="flex justify-center p-6">
        <Spinner />
      </div>
    );
  if (error || !data) return <p className="p-4 text-sm text-bad">{errorMessage(error)}</p>;

  return (
    <div className="flex flex-col gap-5 border-t border-line p-4 sm:p-5">
      <div className="grid gap-4 md:grid-cols-2">
        {CATEGORIES.map((cat) => {
          const vals = data.values.filter((v) => v.category === cat);
          if (!vals.length) return null;
          return (
            <div key={cat}>
              <h4 className="mb-2 text-xs font-bold text-muted">{tr.categories[cat]}</h4>
              <dl className="divide-y divide-line rounded-xl border border-line">
                {vals.map((v) => (
                  <div key={v.key} className="flex items-start justify-between gap-3 px-3 py-2">
                    <dt className="text-sm">{loc(v.name_ar, v.name_en)}</dt>
                    <dd className="text-end text-sm font-semibold">
                      {v.value_type === 'text' ? (
                        <span className="font-normal">{v.display}</span>
                      ) : (
                        <>
                          <span className={v.value_type === 'choice' ? '' : 'num'}>{v.display}</span>
                          {v.unit && v.value_type !== 'choice' && <span className="ms-1 text-xs font-normal text-muted">{loc(v.unit, v.unit_en)}</span>}
                          {v.value_type === 'choice' && v.value_text && (
                            <span className="block text-xs font-normal text-muted">{v.value_text}</span>
                          )}
                        </>
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          );
        })}
      </div>

      <div>
        <h4 className="mb-2 text-xs font-bold text-muted">{tr.sessions.results}</h4>
        <ResultCards results={data.results} />
      </div>

      <div>
        <h4 className="mb-2 flex items-center gap-1.5 text-xs font-bold text-muted">
          <MessageSquare className="h-3.5 w-3.5" />
          {tr.sessions.comments}
        </h4>
        {data.comments.length === 0 ? (
          <p className="text-sm text-muted">{tr.sessions.noComments}</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {data.comments.map((c) => (
              <li key={c.id} className="rounded-xl border-s-4 border-primary bg-primary/5 px-3 py-2">
                <p className="whitespace-pre-line text-sm leading-relaxed">{c.body}</p>
                <p className="mt-1 text-[11px] text-muted">
                  {c.author_name} · {fmtDateTime(c.created_at)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function SessionCard({
  session,
  canEdit,
  onEdit,
  onDelete,
}: {
  session: Session;
  canEdit: boolean;
  onEdit?: (s: Session) => void;
  onDelete?: (s: Session) => void;
}) {
  const [open, setOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const weight = session.values.find((v) => v.key === 'weight');
  const exportPdf = async () => {
    setExporting(true);
    try {
      await downloadPdf(`/pdf/session/${session.id}`);
      toast.success(tr.pdf.exported);
    } catch (err) {
      toast.error(errorMessage(err) || tr.pdf.exportFailed);
    } finally {
      setExporting(false);
    }
  };
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-3 p-3 sm:p-4">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="flex min-w-0 flex-1 items-center gap-3 text-start"
        >
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <CalendarDays className="h-5 w-5" />
          </span>
          <span className="min-w-0">
            <span className="block font-bold">{fmtDate(session.session_date)}</span>
            <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
              <span>
                <span className="num">{session.values.length}</span> {tr.sessions.values}
              </span>
              {weight && (
                <span>
                  · <span className="num font-semibold text-ink">{weight.display}</span> {loc(weight.unit, weight.unit_en)}
                </span>
              )}
              {session.trainer_name && (
                <span>
                  · {tr.sessions.recordedBy}: {session.trainer_name}
                </span>
              )}
              {session.comments_count > 0 && (
                <Badge tone="primary">
                  <MessageSquare className="h-3 w-3" />
                  <span className="num">{session.comments_count}</span>
                </Badge>
              )}
            </span>
            {session.notes && <span className="mt-1 block truncate text-xs text-ink/70">{session.notes}</span>}
          </span>
          <ChevronDown className={clsx('ms-auto h-5 w-5 shrink-0 text-muted transition', open && 'rotate-180')} />
        </button>
        <div className="flex shrink-0 items-center">
          <IconButton label={tr.pdf.exportPdf} onClick={exportPdf} disabled={exporting}>
            {exporting ? <Spinner className="h-4 w-4" /> : <FileDown className="h-4 w-4" />}
          </IconButton>
          {canEdit && (
            <>
            <IconButton label={tr.common.edit} onClick={() => onEdit?.(session)}>
              <Pencil className="h-4 w-4" />
            </IconButton>
            <IconButton label={tr.common.delete} onClick={() => onDelete?.(session)} className="hover:bg-bad/10 hover:text-bad">
              <Trash2 className="h-4 w-4" />
            </IconButton>
            </>
          )}
        </div>
      </div>
      {open && <SessionBody sessionId={session.id} />}
    </Card>
  );
}

export function SessionHistory({
  clientId,
  canEdit,
  onEdit,
}: {
  clientId: number;
  canEdit: boolean;
  onEdit?: (s: Session) => void;
}) {
  const { data, isLoading, error, refetch } = useSessions(clientId);
  const invalidate = useInvalidateClient();
  const [toDelete, setToDelete] = useState<Session | null>(null);

  const del = useMutation({
    mutationFn: (s: Session) => sessionsApi.remove(s.id),
    onSuccess: async () => {
      toast.success(tr.sessions.deleted);
      setToDelete(null);
      await invalidate(clientId);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  if (isLoading)
    return (
      <div className="flex flex-col gap-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );
  if (error) return <ErrorState message={errorMessage(error)} onRetry={() => refetch()} />;
  if (!data?.length)
    return (
      <Card>
        <EmptyState
          icon={<CalendarDays className="h-6 w-6" />}
          title={tr.sessions.empty}
          description={canEdit ? tr.sessions.emptyTrainer : tr.sessions.emptyClient}
        />
      </Card>
    );

  return (
    <div className="flex flex-col gap-3">
      {data.map((s) => (
        <SessionCard key={s.id} session={s} canEdit={canEdit} onEdit={onEdit} onDelete={setToDelete} />
      ))}
      {canEdit && (
        <ConfirmDialog
          open={!!toDelete}
          title={tr.sessions.deleteTitle}
          text={`${toDelete ? fmtDate(toDelete.session_date) + ' — ' : ''}${tr.sessions.deleteText}`}
          onConfirm={() => toDelete && del.mutate(toDelete)}
          onClose={() => setToDelete(null)}
          loading={del.isPending}
        />
      )}
    </div>
  );
}
