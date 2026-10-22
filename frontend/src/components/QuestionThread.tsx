import { useMutation, useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';
import { CalendarDays, ExternalLink, HelpCircle, Lock, Send } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { clientsApi, questionsApi } from '@/api/endpoints';
import type { Question, QuestionStatus } from '@/api/types';
import { useCurrentUser } from '@/hooks/useAuth';
import { qk, useQuestions, useSessions } from '@/hooks/queries';
import { tr } from '@/i18n';
import { fmtDate, fmtDateTime } from '@/lib/format';
import { Badge, Button, Card, EmptyState, ErrorState, Select, Skeleton, Textarea } from './ui';

const statusTone: Record<QuestionStatus, 'warn' | 'good' | 'neutral'> = { open: 'warn', answered: 'good', closed: 'neutral' };

function useInvalidateQuestions() {
  const qc = useQueryClient();
  return (clientId: number) =>
    Promise.all([
      qc.invalidateQueries({ queryKey: qk.questions(clientId) }),
      qc.invalidateQueries({ queryKey: ['inbox'] }),
      qc.invalidateQueries({ queryKey: ['clients'] }),
      qc.invalidateQueries({ queryKey: ['admin', 'stats'] }),
    ]);
}

export function QuestionCard({ question, showClient }: { question: Question; showClient?: boolean }) {
  const user = useCurrentUser();
  const isStaff = user.role !== 'client';
  const invalidate = useInvalidateQuestions();
  const [reply, setReply] = useState('');

  const send = useMutation({
    mutationFn: () => questionsApi.reply(question.id, reply.trim()),
    onSuccess: async () => {
      setReply('');
      toast.success(tr.questions.replied);
      await invalidate(question.client_id);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const setStatus = useMutation({
    mutationFn: (s: QuestionStatus) => questionsApi.setStatus(question.id, s),
    onSuccess: async () => {
      toast.success(tr.questions.statusUpdated);
      await invalidate(question.client_id);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const closed = question.status === 'closed';
  const clientLink = user.role === 'admin' ? `/admin/clients/${question.client_id}` : `/trainer/clients/${question.client_id}`;

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-3 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={statusTone[question.status]}>{tr.questionStatus[question.status]}</Badge>
            {question.session_date && (
              <Badge tone="accent">
                <CalendarDays className="h-3 w-3" />
                {fmtDate(question.session_date)}
              </Badge>
            )}
            {showClient && (
              <Link to={`${clientLink}?tab=questions`} className="inline-flex items-center gap-1 text-sm font-bold text-primary hover:underline">
                {question.client_name}
                <ExternalLink className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>
          <span className="text-[11px] text-muted">{fmtDateTime(question.created_at)}</span>
        </div>

        <div className="rounded-xl bg-surface-2 px-3.5 py-3">
          {!showClient && isStaff && <p className="mb-1 text-xs font-semibold text-muted">{question.client_name}</p>}
          <p className="whitespace-pre-line text-sm leading-relaxed">{question.body}</p>
        </div>

        {question.replies.length > 0 && (
          <ul className="flex flex-col gap-2">
            {question.replies.map((r) => {
              const fromClient = r.author_role === 'client';
              const mine = r.author_id === user.id;
              return (
                <li
                  key={r.id}
                  className={clsx(
                    'max-w-[88%] rounded-2xl px-3.5 py-2.5',
                    fromClient ? 'self-start bg-surface-2' : 'self-end border-s-4 border-primary bg-primary/10',
                  )}
                >
                  <p className="whitespace-pre-line text-sm leading-relaxed">{r.body}</p>
                  <p className="mt-1 text-[11px] text-muted">
                    {mine ? tr.questions.you : r.author_name} · {fmtDateTime(r.created_at)}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="border-t border-line bg-surface-2/40 p-3">
        {closed && !isStaff ? (
          <p className="flex items-center gap-1.5 text-xs text-muted">
            <Lock className="h-3.5 w-3.5" />
            {tr.questions.closedNotice}
          </p>
        ) : (
          <form
            className="flex flex-col gap-2 sm:flex-row sm:items-end"
            onSubmit={(e) => {
              e.preventDefault();
              if (reply.trim()) send.mutate();
            }}
          >
            <Textarea
              aria-label={tr.questions.reply}
              rows={2}
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              placeholder={isStaff ? tr.questions.replyPlaceholder : tr.questions.followUpPlaceholder}
              wrapperClassName="flex-1"
              maxLength={5000}
            />
            <div className="flex gap-2">
              <Button type="submit" loading={send.isPending} disabled={!reply.trim()} icon={<Send className="h-4 w-4 rtl:-scale-x-100" />}>
                {tr.questions.reply}
              </Button>
              {isStaff && (
                <Select
                  aria-label={tr.questions.status}
                  value={question.status}
                  onChange={(e) => setStatus.mutate(e.target.value as QuestionStatus)}
                  disabled={setStatus.isPending}
                  className="h-10 py-0"
                >
                  {(['open', 'answered', 'closed'] as QuestionStatus[]).map((s) => (
                    <option key={s} value={s}>
                      {tr.questionStatus[s]}
                    </option>
                  ))}
                </Select>
              )}
            </div>
          </form>
        )}
      </div>
    </Card>
  );
}

function AskForm({ clientId }: { clientId: number }) {
  const sessions = useSessions(clientId);
  const invalidate = useInvalidateQuestions();
  const [body, setBody] = useState('');
  const [sessionId, setSessionId] = useState('');

  const ask = useMutation({
    mutationFn: () => clientsApi.ask(clientId, { body: body.trim(), session_id: sessionId ? Number(sessionId) : null }),
    onSuccess: async () => {
      setBody('');
      setSessionId('');
      toast.success(tr.questions.asked);
      await invalidate(clientId);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <Card className="p-4 sm:p-5">
      <h2 className="mb-3 flex items-center gap-2 font-bold">
        <HelpCircle className="h-5 w-5 text-primary" />
        {tr.questions.askTitle}
      </h2>
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (body.trim()) ask.mutate();
        }}
      >
        <Textarea
          aria-label={tr.questions.askPlaceholder}
          placeholder={tr.questions.askPlaceholder}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={3}
          maxLength={5000}
        />
        <div className="flex flex-wrap items-end gap-3">
          <Select
            label={tr.questions.aboutSession}
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            wrapperClassName="min-w-[12rem] flex-1"
          >
            <option value="">{tr.questions.noSession}</option>
            {sessions.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {fmtDate(s.session_date)}
              </option>
            ))}
          </Select>
          <Button type="submit" loading={ask.isPending} disabled={!body.trim()} icon={<Send className="h-4 w-4 rtl:-scale-x-100" />}>
            {tr.questions.ask}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export function QuestionThread({ clientId, mode }: { clientId: number; mode: 'staff' | 'client' }) {
  const questions = useQuestions(clientId);
  return (
    <div className="flex flex-col gap-4">
      {mode === 'client' && <AskForm clientId={clientId} />}
      {questions.isLoading ? (
        <Skeleton className="h-40" />
      ) : questions.error ? (
        <ErrorState message={errorMessage(questions.error)} onRetry={() => questions.refetch()} />
      ) : !questions.data?.length ? (
        <Card>
          <EmptyState
            icon={<HelpCircle className="h-6 w-6" />}
            title={tr.questions.empty}
            description={mode === 'client' ? tr.questions.emptyClient : tr.questions.emptyTrainer}
          />
        </Card>
      ) : (
        questions.data.map((q) => <QuestionCard key={q.id} question={q} />)
      )}
    </div>
  );
}
