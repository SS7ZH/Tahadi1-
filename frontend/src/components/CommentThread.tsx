import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarDays, MessageSquare, Send, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { clientsApi, commentsApi } from '@/api/endpoints';
import type { Comment } from '@/api/types';
import { useCurrentUser } from '@/hooks/useAuth';
import { qk, useComments, useSessions } from '@/hooks/queries';
import { ar } from '@/i18n/ar';
import { fmtDate, fmtDateTime } from '@/lib/format';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, IconButton, Select, Skeleton, Textarea } from './ui';

export function CommentThread({ clientId, canWrite }: { clientId: number; canWrite: boolean }) {
  const user = useCurrentUser();
  const qc = useQueryClient();
  const comments = useComments(clientId);
  const sessions = useSessions(clientId);
  const [body, setBody] = useState('');
  const [sessionId, setSessionId] = useState<string>('');
  const [toDelete, setToDelete] = useState<Comment | null>(null);

  const refresh = () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: qk.comments(clientId) }),
      qc.invalidateQueries({ queryKey: qk.sessions(clientId) }),
      qc.invalidateQueries({ queryKey: ['session'] }),
    ]);

  const add = useMutation({
    mutationFn: () => clientsApi.addComment(clientId, { body: body.trim(), session_id: sessionId ? Number(sessionId) : null }),
    onSuccess: async () => {
      setBody('');
      toast.success(ar.comments.added);
      await refresh();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const del = useMutation({
    mutationFn: (c: Comment) => commentsApi.remove(c.id),
    onSuccess: async () => {
      setToDelete(null);
      toast.success(ar.common.deleted);
      await refresh();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const dateOf = (id: number | null) => sessions.data?.find((s) => s.id === id)?.session_date;

  return (
    <div className="flex flex-col gap-4">
      {canWrite && (
        <Card className="p-4 sm:p-5">
          <form
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (body.trim()) add.mutate();
            }}
          >
            <Textarea
              aria-label={ar.comments.placeholder}
              placeholder={ar.comments.placeholder}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              maxLength={5000}
            />
            <div className="flex flex-wrap items-end gap-3">
              <Select
                aria-label={ar.comments.onSession}
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                wrapperClassName="min-w-[12rem] flex-1 sm:flex-none"
              >
                <option value="">{ar.comments.general}</option>
                {sessions.data?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {ar.comments.session}: {fmtDate(s.session_date)}
                  </option>
                ))}
              </Select>
              <Button type="submit" loading={add.isPending} disabled={!body.trim()} icon={<Send className="h-4 w-4 -scale-x-100" />}>
                {ar.common.send}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {comments.isLoading ? (
        <Skeleton className="h-40" />
      ) : comments.error ? (
        <ErrorState message={errorMessage(comments.error)} onRetry={() => comments.refetch()} />
      ) : !comments.data?.length ? (
        <Card>
          <EmptyState
            icon={<MessageSquare className="h-6 w-6" />}
            title={ar.comments.empty}
            description={canWrite ? ar.comments.emptyHint : ar.comments.emptyClient}
          />
        </Card>
      ) : (
        <ul className="flex flex-col gap-3">
          {comments.data.map((c) => (
            <li key={c.id}>
              <Card className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
                      {c.author_name?.charAt(0) ?? '؟'}
                    </span>
                    <div>
                      <p className="text-sm font-semibold">{c.author_name ?? '—'}</p>
                      <p className="text-[11px] text-muted">{fmtDateTime(c.created_at)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    {c.session_id ? (
                      <Badge tone="accent">
                        <CalendarDays className="h-3 w-3" />
                        {fmtDate(dateOf(c.session_id))}
                      </Badge>
                    ) : (
                      <Badge>{ar.comments.general}</Badge>
                    )}
                    {canWrite && (user.role === 'admin' || c.author_id === user.id) && (
                      <IconButton label={ar.common.delete} onClick={() => setToDelete(c)} className="h-8 w-8 hover:text-bad">
                        <Trash2 className="h-4 w-4" />
                      </IconButton>
                    )}
                  </div>
                </div>
                <p className="mt-3 whitespace-pre-line text-sm leading-relaxed">{c.body}</p>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={!!toDelete}
        title={ar.comments.deleteTitle}
        text={ar.comments.deleteText}
        onConfirm={() => toDelete && del.mutate(toDelete)}
        onClose={() => setToDelete(null)}
        loading={del.isPending}
      />
    </div>
  );
}
