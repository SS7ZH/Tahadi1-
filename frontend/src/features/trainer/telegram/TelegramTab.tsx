/**
 * The coach's view of a Telegram player (ADR-0011): group link, AI summary, drafts to approve,
 * questions from the group and squat videos. Players never log in; everything happens here and
 * in the Telegram group.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bot, CheckCircle2, Clapperboard, ExternalLink, Link2, MessageCircleQuestion, RefreshCw, Send, Unlink, XCircle } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { telegramApi, type AgentDraft, type GroupCode, type SquatCheck, type SquatErrorType } from '@/api/telegram';
import { Badge, Button, Card, CardHeader, Input, Spinner, Textarea } from '@/components/ui';
import { useQuestions } from '@/hooks/queries';
import { loc } from '@/i18n';
import { fmtDate } from '@/lib/format';
import { GroupLinkSteps } from './GroupLinkSteps';

const ALERTS: Record<string, [string, string]> = {
  stalled: ['الوزن ثابت منذ 3 أسابيع', 'Weight stalled for 3 weeks'],
  no_checkin: ['لا يوجد قياس منذ 10 أيام أو أكثر', 'No check-in for 10+ days'],
};
const ERROR_LABELS: Record<SquatErrorType, [string, string]> = {
  shallow_depth: ['نزول غير كافٍ', 'Not deep enough'],
  knees_caving: ['الركبتان للداخل', 'Knees caving in'],
  back_lean: ['ميلان الظهر', 'Back leaning'],
};

function SourceBadge({ source }: { source: 'agent' | 'template' }) {
  return source === 'agent' ? (
    <Badge tone="good"><Bot className="h-3 w-3" /> {loc('كتبه الوكيل الذكي', 'Written by the AI agent')}</Badge>
  ) : (
    <Badge tone="warn">{loc('نص جاهز (الوكيل غير متاح)', 'Template text (agent unavailable)')}</Badge>
  );
}

// ------------------------------------------------------------------ coach's own Telegram

function CoachTelegramBanner() {
  const me = useQuery({ queryKey: ['me-telegram'], queryFn: telegramApi.myTelegram });
  const link = useMutation({
    mutationFn: telegramApi.myTelegramLink,
    onSuccess: (r) => window.open(r.url, '_blank', 'noopener'),
    onError: (e) => toast.error(errorMessage(e)),
  });
  if (!me.data || me.data.linked) return null;
  return (
    <Card className="flex flex-wrap items-center gap-3 border-warn/40 p-4">
      <p className="min-w-0 flex-1 text-sm">
        {loc(
          'اربط حسابك في تيليجرام أولًا: لتستلم مسودات الردود وتعتمدها بزر، ولتستطيع ربط مجموعات اللاعبين.',
          'Link your own Telegram first: you will receive reply drafts to approve with a button, and can link players\' groups.',
        )}
      </p>
      <Button size="sm" icon={<ExternalLink className="h-4 w-4" />} loading={link.isPending} onClick={() => link.mutate()}>
        {loc('ربط حسابي بتيليجرام', 'Link my Telegram')}
      </Button>
      <Button size="sm" variant="ghost" icon={<RefreshCw className="h-4 w-4" />} onClick={() => me.refetch()}>
        {loc('تحقق', 'Check')}
      </Button>
    </Card>
  );
}

// ------------------------------------------------------------------ group

function GroupCard({ clientId }: { clientId: number }) {
  const qc = useQueryClient();
  const clients = useQuery({ queryKey: ['telegram-clients'], queryFn: telegramApi.clients });
  const me = useQuery({ queryKey: ['me-telegram'], queryFn: telegramApi.myTelegram });
  const [code, setCode] = useState<GroupCode | null>(null);
  const info = clients.data?.find((c) => c.id === clientId);
  const newCode = useMutation({ mutationFn: () => telegramApi.groupCode(clientId), onSuccess: setCode, onError: (e) => toast.error(errorMessage(e)) });
  const unlink = useMutation({
    mutationFn: () => telegramApi.unlink(clientId),
    onSuccess: async () => {
      toast.success(loc('تم إلغاء ربط المجموعة', 'Group unlinked'));
      await qc.invalidateQueries({ queryKey: ['telegram-clients'] });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <Card>
      <CardHeader
        title={loc('مجموعة تيليجرام', 'Telegram group')}
        icon={<Link2 className="h-5 w-5" />}
        actions={info?.linked ? <Badge tone="good">{loc('مرتبطة ✅', 'Linked ✅')}</Badge> : <Badge tone="warn">{loc('غير مرتبطة', 'Not linked')}</Badge>}
      />
      <div className="flex flex-col gap-3 p-4">
        {clients.isLoading && <Spinner />}
        {info?.linked && (
          <>
            {info.invite_url ? (
              <p className="text-sm">
                {loc('رابط دعوة اللاعب للمجموعة: ', 'Invite link for the player: ')}
                <a href={info.invite_url} target="_blank" rel="noreferrer" dir="ltr" className="font-semibold text-primary underline">{info.invite_url}</a>
              </p>
            ) : (
              <p className="text-sm text-muted">{loc('اجعل البوت مشرفًا ليُنشئ رابط دعوة، أو أضف اللاعب يدويًا.', 'Make the bot an admin so it can create an invite link, or add the player manually.')}</p>
            )}
            <div>
              <Button size="sm" variant="outline" icon={<Unlink className="h-4 w-4" />} loading={unlink.isPending} onClick={() => unlink.mutate()}>
                {loc('إلغاء ربط المجموعة', 'Unlink group')}
              </Button>
            </div>
          </>
        )}
        {info && !info.linked && (
          code ? (
            <GroupLinkSteps code={code} botUsername={me.data?.bot_username} />
          ) : (
            <div>
              <Button size="sm" icon={<Link2 className="h-4 w-4" />} loading={newCode.isPending} onClick={() => newCode.mutate()}>
                {loc('ربط مجموعة تيليجرام', 'Link a Telegram group')}
              </Button>
            </div>
          )
        )}
      </div>
    </Card>
  );
}

// ------------------------------------------------------------------ AI summary

function SummaryCard({ clientId }: { clientId: number }) {
  const summary = useQuery({ queryKey: ['agent-summary', clientId], queryFn: () => telegramApi.summary(clientId) });
  return (
    <Card>
      <CardHeader
        title={loc('تحليل التقدم الذكي', 'AI progress summary')}
        icon={<Bot className="h-5 w-5" />}
        actions={<Button size="sm" variant="ghost" icon={<RefreshCw className="h-4 w-4" />} onClick={() => summary.refetch()} loading={summary.isFetching}>{loc('تحديث', 'Refresh')}</Button>}
      />
      <div className="flex flex-col gap-2 p-4">
        {summary.isLoading && <Spinner />}
        {summary.data && (
          <>
            <div className="flex flex-wrap gap-2">
              <SourceBadge source={summary.data.source} />
              {summary.data.alerts.map((a) => <Badge key={a} tone="bad">{loc(...ALERTS[a])}</Badge>)}
            </div>
            <p className="rounded-xl border border-line bg-surface-2 px-4 py-3 text-sm leading-relaxed">{loc(summary.data.summary_ar, summary.data.summary_en)}</p>
          </>
        )}
      </div>
    </Card>
  );
}

// ------------------------------------------------------------------ drafts

function DraftItem({ draft, question }: { draft: AgentDraft; question?: string }) {
  const qc = useQueryClient();
  const [text, setText] = useState(draft.text);
  const refresh = () => Promise.all([qc.invalidateQueries({ queryKey: ['agent-drafts', draft.client_id] }), qc.invalidateQueries({ queryKey: ['questions'] })]);
  const approve = useMutation({
    mutationFn: () => telegramApi.approve(draft.id, text),
    onSuccess: async (r) => {
      if (r.telegram_sent) toast.success(loc('تم الاعتماد والإرسال للمجموعة', 'Approved and sent to the group'));
      else if (r.telegram_linked === false) toast.warning(loc('تم الاعتماد، لكن اللاعب غير مرتبط بمجموعة فلم يُرسل', 'Approved, but the player has no linked group so it was not sent'));
      else toast.error(loc('تم الاعتماد، لكن تعذر الإرسال لتيليجرام', 'Approved, but sending to Telegram failed'));
      await refresh();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const reject = useMutation({
    mutationFn: () => telegramApi.reject(draft.id),
    onSuccess: async () => {
      toast.info(loc('تم رفض المسودة', 'Draft rejected'));
      await refresh();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const pending = draft.status === 'pending';
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-line p-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
        <SourceBadge source={draft.source} />
        {draft.status === 'approved' && <Badge tone="good"><CheckCircle2 className="h-3 w-3" /> {draft.telegram_sent ? loc('أُرسلت', 'Sent') : loc('معتمدة', 'Approved')}</Badge>}
        {draft.status === 'rejected' && <Badge tone="bad"><XCircle className="h-3 w-3" /> {loc('مرفوضة', 'Rejected')}</Badge>}
        <span>{fmtDate(draft.created_at)}</span>
      </div>
      {question && <p className="text-sm"><MessageCircleQuestion className="me-1 inline h-4 w-4 text-primary" />{question}</p>}
      {pending ? (
        <>
          <Textarea rows={4} value={text} onChange={(e) => setText(e.target.value)} />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" icon={<Send className="h-4 w-4" />} loading={approve.isPending} disabled={!text.trim()} onClick={() => approve.mutate()}>
              {loc('اعتماد وإرسال', 'Approve & send')}
            </Button>
            <Button size="sm" variant="outline" icon={<XCircle className="h-4 w-4" />} loading={reject.isPending} onClick={() => reject.mutate()}>
              {loc('رفض', 'Reject')}
            </Button>
          </div>
        </>
      ) : (
        <p className="whitespace-pre-line text-sm text-ink/80">{draft.text}</p>
      )}
    </div>
  );
}

function DraftsCard({ clientId }: { clientId: number }) {
  const qc = useQueryClient();
  const drafts = useQuery({ queryKey: ['agent-drafts', clientId], queryFn: () => telegramApi.drafts(clientId) });
  const questions = useQuestions(clientId);
  const qText = (id: number | null) => (id ? questions.data?.find((q) => q.id === id)?.body : undefined);
  const create = useMutation({
    mutationFn: () => telegramApi.createDraft(clientId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agent-drafts', clientId] }),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const draftQuestion = useMutation({
    mutationFn: (qid: number) => telegramApi.draftForQuestion(qid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agent-drafts', clientId] }),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const pending = drafts.data?.filter((d) => d.status === 'pending') ?? [];
  const recent = drafts.data?.filter((d) => d.status !== 'pending').slice(0, 5) ?? [];
  const draftedQuestions = new Set(drafts.data?.map((d) => d.question_id).filter(Boolean));
  const openTelegram = questions.data?.filter((q) => q.source === 'telegram' && q.status === 'open' && !draftedQuestions.has(q.id)) ?? [];

  return (
    <Card>
      <CardHeader
        title={loc('مسودات الردود (بانتظار اعتمادك)', 'Reply drafts (waiting for you)')}
        subtitle={loc('تصلك أيضًا في تيليجرام بأزرار اعتماد / تعديل / رفض', 'Also sent to you on Telegram with Approve / Edit / Reject buttons')}
        icon={<Bot className="h-5 w-5" />}
        actions={<Button size="sm" variant="outline" icon={<RefreshCw className="h-4 w-4" />} loading={create.isPending} onClick={() => create.mutate()}>{loc('مسودة جديدة', 'New draft')}</Button>}
      />
      <div className="flex flex-col gap-3 p-4">
        {drafts.isLoading && <Spinner />}
        {openTelegram.map((q) => (
          <div key={q.id} className="flex flex-wrap items-center gap-2 rounded-xl bg-surface-2 p-3 text-sm">
            <MessageCircleQuestion className="h-4 w-4 text-primary" />
            <span className="min-w-0 flex-1">{q.body}</span>
            <Button size="sm" variant="outline" loading={draftQuestion.isPending && draftQuestion.variables === q.id} onClick={() => draftQuestion.mutate(q.id)}>
              {loc('اقتراح رد', 'Suggest a reply')}
            </Button>
          </div>
        ))}
        {pending.map((d) => <DraftItem key={d.id} draft={d} question={qText(d.question_id)} />)}
        {!drafts.isLoading && pending.length === 0 && openTelegram.length === 0 && (
          <p className="text-sm text-muted">{loc('لا توجد مسودات بانتظارك.', 'No drafts waiting for you.')}</p>
        )}
        {recent.length > 0 && (
          <details className="text-sm">
            <summary className="cursor-pointer text-muted">{loc('آخر القرارات', 'Recent decisions')}</summary>
            <div className="mt-2 flex flex-col gap-2">{recent.map((d) => <DraftItem key={d.id} draft={d} question={qText(d.question_id)} />)}</div>
          </details>
        )}
      </div>
    </Card>
  );
}

// ------------------------------------------------------------------ squat checks

function ReviewForm({ check, clientId }: { check: SquatCheck; clientId: number }) {
  const qc = useQueryClient();
  const [reps, setReps] = useState('');
  const [errors, setErrors] = useState<SquatErrorType[]>([]);
  const save = useMutation({
    mutationFn: () => telegramApi.reviewSquatCheck(check.id, { reps: Number(reps), errors: errors.map((type) => ({ type })), confidence: 1 }),
    onSuccess: async () => {
      toast.success(loc('تم حفظ التحليل؛ سيستخدمه مساعد المدرب في الردود', 'Saved; the coach assistant will use it in replies'));
      await qc.invalidateQueries({ queryKey: ['squat-checks', clientId] });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <div className="flex flex-wrap items-end gap-3">
      <Input label={loc('عدد التكرارات', 'Reps')} type="number" min={0} dir="ltr" className="w-24" value={reps} onChange={(e) => setReps(e.target.value)} />
      {(Object.keys(ERROR_LABELS) as SquatErrorType[]).map((k) => (
        <label key={k} className="flex items-center gap-1.5 text-sm">
          <input type="checkbox" checked={errors.includes(k)} onChange={(e) => setErrors(e.target.checked ? [...errors, k] : errors.filter((x) => x !== k))} />
          {loc(...ERROR_LABELS[k])}
        </label>
      ))}
      <Button size="sm" loading={save.isPending} disabled={reps === ''} onClick={() => save.mutate()}>{loc('حفظ التحليل', 'Save review')}</Button>
    </div>
  );
}

function SquatCard({ clientId }: { clientId: number }) {
  const checks = useQuery({ queryKey: ['squat-checks', clientId], queryFn: () => telegramApi.squatChecks(clientId) });
  const watch = async (id: number) => {
    try {
      const { url } = await telegramApi.squatVideo(id);
      window.open(url, '_blank', 'noopener');
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };
  return (
    <Card>
      <CardHeader title={loc('فحوصات السكوات', 'Squat checks')} subtitle={loc('فيديوهات اللاعب من تيليجرام', "The player's videos from Telegram")} icon={<Clapperboard className="h-5 w-5" />} />
      <div className="flex flex-col gap-3 p-4">
        {checks.isLoading && <Spinner />}
        {checks.data?.length === 0 && <p className="text-sm text-muted">{loc('لم يرسل اللاعب فيديو بعد.', 'No videos yet.')}</p>}
        {checks.data?.map((c) => (
          <div key={c.id} className="flex flex-col gap-2 rounded-xl border border-line p-3">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-muted">{fmtDate(c.created_at)}</span>
              {c.status === 'awaiting_review' ? <Badge tone="warn">{loc('بانتظار مراجعتك', 'Waiting for your review')}</Badge> : <Badge tone="good">{loc('تم التحليل', 'Analysed')}</Badge>}
              {c.reps != null && <span>{loc(`${c.reps} تكرار`, `${c.reps} reps`)}</span>}
              {c.errors.map((e, i) => <Badge key={i} tone="bad">{loc(...ERROR_LABELS[e.type])}</Badge>)}
              {c.has_video && (
                <Button size="sm" variant="ghost" icon={<ExternalLink className="h-4 w-4" />} onClick={() => watch(c.id)}>{loc('مشاهدة', 'Watch')}</Button>
              )}
            </div>
            {c.status === 'awaiting_review' && <ReviewForm check={c} clientId={clientId} />}
          </div>
        ))}
      </div>
    </Card>
  );
}

export function TelegramTab({ clientId }: { clientId: number }) {
  return (
    <div className="flex flex-col gap-4">
      <CoachTelegramBanner />
      <GroupCard clientId={clientId} />
      <DraftsCard clientId={clientId} />
      <SummaryCard clientId={clientId} />
      <SquatCard clientId={clientId} />
    </div>
  );
}
