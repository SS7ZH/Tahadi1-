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
  RefreshCw, Bot, Send, Clock, SendHorizontal,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardHeader, Button, Badge, Spinner, Input } from '@/components/ui';
import { demoApi, type ProgressSummary, type DraftReply } from './demoApi';

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
  clients: string[];
  selected: string;
  onSelect: (c: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-muted flex items-center gap-1.5">
        <Users className="h-4 w-4" /> اختر المشترك:
      </label>
      <div className="flex flex-wrap gap-2">
        {clients.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => onSelect(c)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              selected === c
                ? 'bg-primary text-on-primary shadow-sm'
                : 'bg-surface-2 text-ink hover:bg-line/70'
            }`}
          >
            {c}
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
            disabled={draftStatus === 'approved'}
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

/* ---- المكون الرئيسي ---- */
export function CoachView({ onClientChange }: { onClientChange?: (c: string) => void }) {
  const clients = demoApi.clients();
  const [selectedClient, setSelectedClient] = useState(clients[0]);
  const [summary, setSummary] = useState<ProgressSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [draft, setDraft] = useState<DraftReply | null>(null);
  const [draftStatus, setDraftStatus] = useState<DraftStatus>('idle');
  const [loadingDraft, setLoadingDraft] = useState(false);
  const [loadingApprove, setLoadingApprove] = useState(false);
  const [loadingReject, setLoadingReject] = useState(false);
  const [editedText, setEditedText] = useState('');

  // محاكي رسائل تيليجرام
  const [telegramMsg, setTelegramMsg] = useState('weight 82');
  const [sendingTelegram, setSendingTelegram] = useState(false);

  const loadSummary = useCallback(async (client: string) => {
    setLoadingSummary(true);
    setSummary(null);
    setDraft(null);
    setDraftStatus('idle');
    setEditedText('');
    try {
      const data = await demoApi.summary(client);
      setSummary(data);
    } catch {
      toast.error('تعذر جلب ملخص المشترك');
    } finally {
      setLoadingSummary(false);
    }
  }, []);

  useEffect(() => {
    loadSummary(selectedClient);
    onClientChange?.(selectedClient);
  }, [selectedClient, loadSummary, onClientChange]);

  const handleClientSelect = (c: string) => {
    setSelectedClient(c);
  };

  const handleGenerateDraft = async () => {
    setLoadingDraft(true);
    try {
      const d = await demoApi.draft(selectedClient);
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
    if (!draft) return;
    setLoadingApprove(true);
    try {
      await demoApi.approveDraft(selectedClient, editedText);
      setDraftStatus('approved');
      toast.success(`تم اعتماد الرد وإرساله للمشترك ${selectedClient} عبر تيليجرام`);
    } catch {
      toast.error('تعذر اعتماد الرد');
    } finally {
      setLoadingApprove(false);
    }
  };

  const handleReject = async () => {
    if (!draft) return;
    setLoadingReject(true);
    try {
      await demoApi.rejectDraft(selectedClient);
      setDraftStatus('rejected');
      toast.info('تم رفض المسودة');
    } catch {
      toast.error('تعذر رفض المسودة');
    } finally {
      setLoadingReject(false);
    }
  };

  const handleSendTelegram = async () => {
    if (!telegramMsg.trim()) return;
    setSendingTelegram(true);
    try {
      const res = await demoApi.sendTelegramMessage(telegramMsg.trim(), selectedClient);
      toast.success(`تم استلام رسالة تيليجرام: "${telegramMsg.trim()}"`);
      if (res.weight_kg) {
        toast.info(`سجل وكيل الاستقبال وزناً جديداً: ${res.weight_kg} كجم لـ ${selectedClient}`);
      }
      await loadSummary(selectedClient);
    } catch {
      toast.error('تعذر معالجة رسالة تيليجرام');
    } finally {
      setSendingTelegram(false);
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
          selected={selectedClient}
          onSelect={handleClientSelect}
        />

        {/* محاكي استقبال قياسات تيليجرام */}
        <div className="rounded-xl border border-accent/25 bg-accent/5 p-3.5 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-accent flex items-center gap-1.5">
              <SendHorizontal className="h-3.5 w-3.5" /> استقبال القياسات عبر تيليجرام (Telegram Intake)
            </span>
            <span className="text-[11px] text-muted">جرب إرسال وزن جديد لتحديث الشارت فوراً</span>
          </div>
          <div className="flex gap-2">
            <Input
              value={telegramMsg}
              onChange={(e) => setTelegramMsg(e.target.value)}
              placeholder="مثال: weight 82 أو وزن 82"
              className="text-xs py-1.5"
            />
            <Button
              size="sm"
              loading={sendingTelegram}
              icon={<Send className="h-3.5 w-3.5" />}
              onClick={handleSendTelegram}
            >
              إرسال للبوت
            </Button>
          </div>
        </div>

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
            <div className="rounded-xl bg-surface-2 border border-line px-4 py-3 text-sm leading-relaxed text-ink">
              {summary.aiSummary}
            </div>
          ) : (
            <div className="text-sm text-muted">لا يوجد ملخص متاح حالياً.</div>
          )}
        </div>

        {/* فاصل */}
        <div className="border-t border-line" />

        {/* مسودة الرد */}
        <DraftPanel
          clientName={selectedClient}
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
