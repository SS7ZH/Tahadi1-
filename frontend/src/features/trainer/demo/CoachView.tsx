/**
 * CoachView — لوحة متابعة المشترك ومساعد المدرب الذكي.
 *
 * تتضمن:
 *  - اختيار المشترك من العملاء المسجلين.
 *  - شارت تطور الوزن (weight_kg) عبر الأسابيع.
 *  - ملخص الأداء المولد بالذكاء الاصطناعي (Progress Analyst).
 *  - مسودة الرد التلقائية للمدرب مع خيارات الاعتماد والإرسال أو الرفض.
 *  - ربط فوري مع تيليجرام واستقبال القياسات.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  Users, TrendingUp, MessageSquare, CheckCircle2, XCircle,
  RefreshCw, Bot, Send, Clock, Link2,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardHeader, Button, Badge, Spinner } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { demoApi, type ProgressSummary, type DraftReply, type TelegramLinkClient } from './demoApi';
import { telegramApi, type GroupCode } from '@/api/telegram';
import { GroupLinkSteps } from '../telegram/GroupLinkSteps';

/* ---- تنسيق التاريخ ---- */
function fmtDate(d: string) {
  try {
    const dt = new Date(d);
    return dt.toLocaleDateString('ar-SA', { month: 'short', day: 'numeric' });
  } catch {
    return d;
  }
}

/* ---- المكونات الفرعية ---- */

function ClientSelector({ clients, selected, onSelect }: {
  clients: TelegramLinkClient[];
  selected: number | null;
  onSelect: (id: number) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-muted flex items-center gap-1.5">
        <Users className="h-4 w-4" /> اختر المشترك:
      </label>
      <div className="flex flex-wrap gap-2">
        {clients.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => onSelect(c.id)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              selected === c.id
                ? 'bg-primary text-on-primary shadow-sm'
                : 'bg-surface-2 text-ink hover:bg-line/70'
            }`}
          >
            {c.name}
          </button>
        ))}
      </div>
    </div>
  );
}

function ProgressChart({ data }: { data: ProgressSummary['measurements'] }) {
  if (!data || !data.length) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted">
        لا توجد بيانات قياسات مسجلة
      </div>
    );
  }

  const chartData = data.map((d) => ({ ...d, formattedDate: fmtDate(d.date) }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={chartData} margin={{ top: 10, right: 10, bottom: 5, left: -15 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
        <XAxis dataKey="formattedDate" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} unit=" كجم" domain={['auto', 'auto']} />
        <Tooltip
          contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid #e4e1db', direction: 'rtl' }}
          formatter={(val: number) => [`${val} كجم`, 'الوزن']}
        />
        <Line
          type="monotone"
          dataKey="weight_kg"
          stroke="#f2550d"
          strokeWidth={2.5}
          dot={{ r: 4, fill: '#f2550d' }}
          activeDot={{ r: 6 }}
          name="الوزن"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

type DraftStatus = 'idle' | 'pending' | 'approved' | 'rejected';

/* مصدر النص: وكيل DevAI أو النص الجاهز */
function SourceBadge({ source }: { source?: 'agent' | 'template' }) {
  if (!source) return null;
  return source === 'agent'
    ? <Badge tone="good">كتبه وكيل DevAI</Badge>
    : <Badge tone="warn">نص جاهز (الوكيل غير متاح)</Badge>;
}

const ALERT_LABELS: Record<string, string> = {
  stalled: 'الوزن ثابت منذ 3 أسابيع',
  no_checkin: 'لا يوجد قياس منذ 10 أيام أو أكثر',
};

interface DraftPanelProps {
  clientName: string;
  draft: DraftReply | null;
  draftStatus: DraftStatus;
  loadingDraft: boolean;
  loadingApprove: boolean;
  loadingReject: boolean;
  onGenerate: () => void;
  onApprove: () => void;
  onReject: () => void;
  editedText: string;
  onEditText: (t: string) => void;
}

function DraftPanel({
  draft,
  draftStatus,
  loadingDraft,
  loadingApprove,
  loadingReject,
  onGenerate,
  onApprove,
  onReject,
  editedText,
  onEditText,
}: DraftPanelProps) {
  const statusBadge = {
    idle: null,
    pending: <Badge tone="warn" className="flex items-center gap-1"><Clock className="h-3 w-3" /> بانتظار اعتماد المدرب</Badge>,
    approved: <Badge tone="good" className="flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> تم الاعتماد والإرسال</Badge>,
    rejected: <Badge tone="bad" className="flex items-center gap-1"><XCircle className="h-3 w-3" /> تم الرفض</Badge>,
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm">مسودة الرد الذكية للمدرب</span>
          {statusBadge[draftStatus]}
          {draft && <SourceBadge source={draft.source} />}
        </div>
        <Button
          size="sm"
          variant="outline"
          icon={<RefreshCw className="h-4 w-4" />}
          loading={loadingDraft}
          onClick={onGenerate}
          disabled={draftStatus === 'approved'}
        >
          {draft ? 'إعادة التوليد' : 'توليد مسودة الرد'}
        </Button>
      </div>

      {loadingDraft && (
        <div className="flex items-center gap-2 rounded-xl bg-surface-2 px-4 py-3 text-sm text-muted">
          <Spinner className="h-4 w-4" />
          جارٍ صياغة الرد المقترح بناءً على تقدم المشترك…
        </div>
      )}

      {!loadingDraft && draft && (
        <div className="flex flex-col gap-2">
          <textarea
            value={editedText}
            onChange={(e) => onEditText(e.target.value)}
            rows={4}
            disabled={draftStatus !== 'pending'}
            className="field-input resize-y leading-relaxed text-sm disabled:opacity-60"
            placeholder="نص مسودة الرد الموجه للمشترك…"
          />

          {draftStatus === 'pending' && (
            <div className="flex gap-2">
              <Button
                onClick={onApprove}
                loading={loadingApprove}
                icon={<Send className="h-4 w-4" />}
                className="flex-1"
              >
                اعتماد وإرسال للمشترك عبر تيليجرام
              </Button>
              <Button
                variant="danger"
                onClick={onReject}
                loading={loadingReject}
                icon={<XCircle className="h-4 w-4" />}
              >
                رفض
              </Button>
            </div>
          )}

          {draftStatus === 'approved' && (
            <div className="flex items-center gap-2 rounded-xl bg-good/10 px-4 py-3 text-sm font-semibold text-good">
              <CheckCircle2 className="h-4 w-4" />
              تم اعتماد الرد بنجاح! تم إرسال الرسالة إلى تيليجرام المشترك.
            </div>
          )}

          {draftStatus === 'rejected' && (
            <div className="flex items-center gap-2 rounded-xl bg-bad/10 px-4 py-3 text-sm font-semibold text-bad">
              <XCircle className="h-4 w-4" />
              تم رفض المسودة. يمكنك الضغط على "إعادة التوليد" لطلب صياغة بديلة.
            </div>
          )}
        </div>
      )}

      {!loadingDraft && !draft && (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-line py-6 text-center">
          <MessageSquare className="h-6 w-6 text-muted" />
          <p className="font-semibold text-xs text-ink">لم يتم توليد مسودة رد بعد</p>
          <p className="text-xs text-muted">اضغط على "توليد مسودة الرد" ليقوم المساعد الذكي بصياغة رسالة للمدرب</p>
        </div>
      )}
    </div>
  );
}

function TelegramLinkPanel({
  client,
  onRefresh,
  refreshing,
}: {
  client: TelegramLinkClient | null;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const { status, user } = useAuth();
  const canManageLinks = status === 'authenticated' && (user?.role === 'trainer' || user?.role === 'admin');
  const [code, setCode] = useState<GroupCode | null>(null);
  const [creatingCode, setCreatingCode] = useState(false);

  useEffect(() => {
    setCode(null);
  }, [client?.id]);

  const createCode = async () => {
    if (!client || client.linked) return;
    setCreatingCode(true);
    try {
      setCode(await telegramApi.groupCode(client.id));
    } catch {
      toast.error('تعذر إنشاء رمز الربط. حدّث قائمة اللاعبين وحاول مجدداً.');
    } finally {
      setCreatingCode(false);
    }
  };

  if (!canManageLinks) {
    return (
      <div className="flex items-center gap-2 border-t border-line pt-4 text-sm text-muted">
        <Link2 className="h-4 w-4" />
        <span>لربط لاعب بمجموعة تيليجرام، سجّل الدخول بحساب مدرب أو إداري.</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 border-t border-line pt-4">
      <div className="flex items-center gap-2">
        <Link2 className="h-4 w-4 text-accent" />
        <span className="font-semibold text-sm">مجموعة تيليجرام للاعب</span>
        <Button size="sm" variant="outline" icon={<RefreshCw className="h-3.5 w-3.5" />} onClick={onRefresh} loading={refreshing}>
          تحديث
        </Button>
      </div>
      <p className="text-xs text-muted">
        {client ? `اللاعب المحدد: ${client.name}. ` : 'اختر لاعباً من القائمة أعلاه. '}
        كل لاعب له مجموعة صغيرة فيها أنت والبوت واللاعب.
      </p>
      {client?.linked ? (
        <p className="text-sm">
          ✅ مرتبط بمجموعة.{' '}
          {client.invite_url && (
            <a className="font-semibold text-primary underline" href={client.invite_url} target="_blank" rel="noreferrer" dir="ltr">
              رابط الدعوة
            </a>
          )}
        </p>
      ) : code ? (
        <GroupLinkSteps code={code} />
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" icon={<Link2 className="h-4 w-4" />} loading={creatingCode} disabled={!client} onClick={createCode}>
            ربط مجموعة تيليجرام
          </Button>
        </div>
      )}
    </div>
  );
}

/* ---- المكون الرئيسي ---- */
export function CoachView() {
  const [clients, setClients] = useState<TelegramLinkClient[]>([]);
  const [loadingClients, setLoadingClients] = useState(true);
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null);
  const [summary, setSummary] = useState<ProgressSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [draft, setDraft] = useState<DraftReply | null>(null);
  const [draftStatus, setDraftStatus] = useState<DraftStatus>('idle');
  const [loadingDraft, setLoadingDraft] = useState(false);
  const [loadingApprove, setLoadingApprove] = useState(false);
  const [loadingReject, setLoadingReject] = useState(false);
  const [editedText, setEditedText] = useState('');
  const selectedClient = clients.find((client) => client.id === selectedClientId) ?? null;

  const loadClients = useCallback(async () => {
    setLoadingClients(true);
    demoApi.telegramClients()
      .then((rows) => {
        setClients(rows);
        setSelectedClientId((current) => rows.some((row) => row.id === current) ? current : rows[0]?.id ?? null);
      })
      .catch(() => toast.error('تعذر تحميل قائمة اللاعبين'))
      .finally(() => setLoadingClients(false));
  }, []);

  useEffect(() => { void loadClients(); }, [loadClients]);

  const loadSummary = useCallback(async (client: TelegramLinkClient) => {
    setLoadingSummary(true);
    setSummary(null);
    setDraft(null);
    setDraftStatus('idle');
    setEditedText('');
    try {
      const data = await demoApi.clientSummary(client.id, client.name);
      setSummary(data);
    } catch {
      toast.error('تعذر جلب ملخص المشترك');
    } finally {
      setLoadingSummary(false);
    }
  }, []);

  useEffect(() => {
    if (selectedClient) loadSummary(selectedClient);
  }, [selectedClient, loadSummary]);

  const handleClientSelect = (id: number) => {
    setSelectedClientId(id);
  };

  const handleGenerateDraft = async () => {
    if (!selectedClient) return;
    setLoadingDraft(true);
    try {
      const d = await demoApi.clientDraft(selectedClient.id, selectedClient.name);
      setDraft(d);
      setEditedText(d.draftText);
      setDraftStatus('pending');
    } catch {
      toast.error('تعذر توليد المسودة');
    } finally {
      setLoadingDraft(false);
    }
  };

  const handleApprove = async () => {
    if (!draft || !selectedClient) return;
    setLoadingApprove(true);
    try {
      const result = await demoApi.approveClientDraft(Number(draft.id), editedText);
      setDraftStatus('approved');
      if (result.telegram_sent) {
        toast.success(`تم اعتماد الرد وإرساله للمشترك ${selectedClient.name} عبر تيليجرام`);
      } else if (!result.telegram_linked) {
        toast.warning(`تم اعتماد الرد، لكن ${selectedClient.name} غير مربوط بتيليجرام فلم يُرسل`);
      } else {
        toast.error('تم اعتماد الرد، لكن تعذر إرساله عبر تيليجرام');
      }
    } catch {
      toast.error('تعذر اعتماد الرد');
    } finally {
      setLoadingApprove(false);
    }
  };

  const handleReject = async () => {
    if (!draft || !selectedClient) return;
    setLoadingReject(true);
    try {
      await demoApi.rejectClientDraft(Number(draft.id));
      setDraftStatus('rejected');
      toast.info('تم رفض المسودة');
    } catch {
      toast.error('تعذر رفض المسودة');
    } finally {
      setLoadingReject(false);
    }
  };

  return (
    <Card className="flex flex-col">
      <CardHeader
        title="لوحة متابعة المشترك ومساعد المدرب"
        subtitle="مخطط القياسات · تحليل التقدم بالذكاء الاصطناعي · مسودات الرد"
        icon={<TrendingUp className="h-5 w-5" />}
        actions={
          <Badge tone="good">متصل بالخادم</Badge>
        }
      />

      <div className="flex flex-col gap-5 p-5">
        {/* اختيار المشترك */}
        <ClientSelector
          clients={clients}
          selected={selectedClientId}
          onSelect={handleClientSelect}
        />
        {loadingClients && <div className="text-sm text-muted"><Spinner className="me-2 inline h-4 w-4" />جارٍ تحميل اللاعبين…</div>}

        <TelegramLinkPanel client={selectedClient} onRefresh={loadClients} refreshing={loadingClients} />

        {/* مخطط القياسات */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary" />
              <span className="font-semibold text-sm">مخطط تطور الوزن (كجم)</span>
            </div>
            <span className="text-xs text-muted">
              {summary?.measurements.length ?? 0} قياسات مسجلة
            </span>
          </div>
          {loadingSummary ? (
            <div className="flex h-48 items-center justify-center">
              <Spinner />
            </div>
          ) : (
            <ProgressChart data={summary?.measurements ?? []} />
          )}
        </div>

        {/* ملخص أداء المشترك */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-accent" />
            <span className="font-semibold text-sm">تحليل التقدم الذكي</span>
          </div>
          {loadingSummary ? (
            <div className="flex flex-col gap-2">
              <div className="h-4 rounded bg-surface-2 animate-pulse" />
              <div className="h-4 rounded bg-surface-2 animate-pulse w-5/6" />
            </div>
          ) : summary?.aiSummary ? (
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <SourceBadge source={summary.source} />
                {(summary.alerts ?? []).map((a) => (
                  <Badge key={a} tone="bad">{ALERT_LABELS[a] ?? a}</Badge>
                ))}
              </div>
              <div className="rounded-xl bg-surface-2 border border-line px-4 py-3 text-sm leading-relaxed text-ink">
                {summary.aiSummary}
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted">لا يوجد ملخص متاح حالياً.</div>
          )}
        </div>

        {/* فاصل */}
        <div className="border-t border-line" />

        {/* مسودة الرد */}
        <DraftPanel
          clientName={selectedClient?.name ?? ''}
          draft={draft}
          draftStatus={draftStatus}
          loadingDraft={loadingDraft}
          loadingApprove={loadingApprove}
          loadingReject={loadingReject}
          onGenerate={handleGenerateDraft}
          onApprove={handleApprove}
          onReject={handleReject}
          editedText={editedText}
          onEditText={setEditedText}
        />
      </div>
    </Card>
  );
}
