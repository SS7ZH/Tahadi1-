/**
 * SquatChecker — فحص أداء السكوات بالرؤية الحاسوبية (MediaPipe Pose).
 *
 * الميزات:
 *  - استخراج نقاط الورك والركبة والكاحل من الويب كام.
 *  - حساب دقيق لزاوية الركبة في الوقت الحقيقي.
 *  - عد التكرارات الصحيحة (وقوف >160°، نزول كامل <100°).
 *  - التنبيه الفوري: "انزل أكثر" عندما يظل الورك أعلى من مستوى الركبة.
 *  - حفظ نتيجة كل جولة في جدول form_checks.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { Camera, AlertTriangle, CheckCircle2, RefreshCw, ArrowDownCircle, Save } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardHeader, Button, Badge } from '@/components/ui';
import { useQuery } from '@tanstack/react-query';
import { telegramApi, type SquatErrorType } from '@/api/telegram';

/* ---- أنواع MediaPipe ---- */
declare global {
  interface Window {
    Pose: new (config: object) => PoseInstance;
    Camera: new (video: HTMLVideoElement, config: object) => CameraInstance;
    POSE_CONNECTIONS: unknown;
    drawConnectors: (ctx: CanvasRenderingContext2D, landmarks: NormalizedLandmarkList, connections: unknown, style: object) => void;
    drawLandmarks: (ctx: CanvasRenderingContext2D, landmarks: NormalizedLandmarkList, style: object) => void;
  }
}

interface NormalizedLandmark {
  x: number;
  y: number;
  z: number;
  visibility?: number;
}
type NormalizedLandmarkList = NormalizedLandmark[];

interface PoseResults {
  poseLandmarks?: NormalizedLandmarkList;
  image: HTMLVideoElement | HTMLImageElement;
}

interface PoseInstance {
  setOptions: (opts: object) => void;
  onResults: (fn: (results: PoseResults) => void) => void;
  send: (input: { image: HTMLVideoElement }) => Promise<void>;
  close: () => void;
}

interface CameraInstance {
  start: () => Promise<void>;
  stop: () => void;
}

const L_HIP = 23;
const L_KNEE = 25;
const L_ANKLE = 27;
const R_HIP = 24;
const R_KNEE = 26;
const R_ANKLE = 28;

const STAND_DEG = 160;
const SQUAT_DEG = 100;

function calculateAngle(a: NormalizedLandmark, b: NormalizedLandmark, c: NormalizedLandmark): number {
  const ba = { x: a.x - b.x, y: a.y - b.y };
  const bc = { x: c.x - b.x, y: c.y - b.y };
  const dot = ba.x * bc.x + ba.y * bc.y;
  const mag = Math.sqrt(ba.x ** 2 + ba.y ** 2) * Math.sqrt(bc.x ** 2 + bc.y ** 2);
  if (mag === 0) return 0;
  return (Math.acos(Math.max(-1, Math.min(1, dot / mag))) * 180) / Math.PI;
}

function pickLandmarks(lms: NormalizedLandmarkList) {
  const lVis = Math.min(lms[L_HIP]?.visibility ?? 0, lms[L_KNEE]?.visibility ?? 0, lms[L_ANKLE]?.visibility ?? 0);
  const rVis = Math.min(lms[R_HIP]?.visibility ?? 0, lms[R_KNEE]?.visibility ?? 0, lms[R_ANKLE]?.visibility ?? 0);
  if (rVis > lVis) return { hip: lms[R_HIP], knee: lms[R_KNEE], ankle: lms[R_ANKLE] };
  return { hip: lms[L_HIP], knee: lms[L_KNEE], ankle: lms[L_ANKLE] };
}

type Phase = 'standing' | 'descending' | 'bottom' | 'ascending';

interface RepState {
  reps: number;
  phase: Phase;
  touchedBottom: boolean;
  errors: string[];
}

interface SquatCheckerProps {
  onSetSaved?: (reps: number) => void;
}

/** Arabic on-screen error -> the error type the backend and the Coach Assistant use. */
function errorType(text: string): SquatErrorType | null {
  if (text.includes('نزول') || text.includes('الورك')) return 'shallow_depth';
  if (text.includes('الركب')) return 'knees_caving';
  if (text.includes('الظهر')) return 'back_lean';
  return null;
}

const CDN_POSE = 'https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js';
const CDN_CAMERA = 'https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js';
const CDN_DRAWING = 'https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js';

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
    const s = document.createElement('script');
    s.src = src;
    s.crossOrigin = 'anonymous';
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(s);
  });
}

export function SquatChecker({ onSetSaved }: SquatCheckerProps) {
  // Sets are saved to a real player (shown to the coach and used by the Coach Assistant).
  const players = useQuery({ queryKey: ['telegram-clients'], queryFn: telegramApi.clients });
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const poseRef = useRef<PoseInstance | null>(null);
  const cameraRef = useRef<CameraInstance | null>(null);
  const repStateRef = useRef<RepState>({ reps: 0, phase: 'standing', touchedBottom: false, errors: [] });

  const [activeClientId, setActiveClientId] = useState<number | null>(null);
  const activeClient = players.data?.find((c) => c.id === activeClientId) ?? players.data?.[0] ?? null;
  const [status, setStatus] = useState<'idle' | 'loading' | 'running' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [reps, setReps] = useState(0);
  const [kneeAngle, setKneeAngle] = useState<number | null>(null);
  const [goLower, setGoLower] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<Phase>('standing');
  const [savingSet, setSavingSet] = useState(false);
  const [lastSavedInfo, setLastSavedInfo] = useState<string | null>(null);

  const cleanup = useCallback(() => {
    cameraRef.current?.stop();
    poseRef.current?.close();
    cameraRef.current = null;
    poseRef.current = null;
  }, []);

  useEffect(() => () => cleanup(), [cleanup]);

  const handleResults = useCallback((results: PoseResults) => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);

    const lms = results.poseLandmarks;
    if (!lms) { ctx.restore(); return; }

    if (window.drawConnectors && window.POSE_CONNECTIONS) {
      window.drawConnectors(ctx, lms, window.POSE_CONNECTIONS, { color: '#f2550d', lineWidth: 3 });
      window.drawLandmarks(ctx, lms, { color: '#ffffff', lineWidth: 1.5, radius: 4 });
    }

    const { hip, knee, ankle } = pickLandmarks(lms);
    if (!hip || !knee || !ankle) { ctx.restore(); return; }

    const deg = calculateAngle(hip, knee, ankle);
    setKneeAngle(Math.round(deg));

    // قاعدة: "انزل أكثر" عندما يظل الورك أعلى من مستوى الركبة
    const hipAboveKnee = hip.y < knee.y;
    const shallowDepth = deg < 135 && hipAboveKnee;
    setGoLower(shallowDepth);

    const state = repStateRef.current;
    let newPhase = state.phase;

    if (deg > STAND_DEG) {
      if (state.phase === 'ascending' && state.touchedBottom) {
        state.reps += 1;
        setReps(state.reps);
      }
      newPhase = 'standing';
      state.touchedBottom = false;
    } else if (deg < SQUAT_DEG) {
      newPhase = 'bottom';
      state.touchedBottom = true;
      if (hipAboveKnee) {
        if (!state.errors.includes('نزول غير كافٍ (الورك أعلى من الركبة)')) {
          state.errors.push('نزول غير كافٍ (الورك أعلى من الركبة)');
        }
      }
    } else if (deg <= STAND_DEG && deg >= SQUAT_DEG) {
      if (state.phase === 'standing' || state.phase === 'ascending') {
        newPhase = 'descending';
      } else if (state.phase === 'bottom') {
        newPhase = 'ascending';
      }
    }

    state.phase = newPhase;
    setCurrentPhase(newPhase);

    // زاوية الركبة
    const kx = knee.x * canvas.width;
    const ky = knee.y * canvas.height;
    ctx.font = 'bold 22px system-ui';
    ctx.fillStyle = deg < SQUAT_DEG ? '#16a34a' : deg > STAND_DEG ? '#94a3b8' : '#f2550d';
    ctx.fillText(`${Math.round(deg)}°`, kx + 12, ky - 10);

    // لافتة "انزل أكثر" على الفيديو
    if (shallowDepth) {
      ctx.fillStyle = 'rgba(220, 38, 38, 0.88)';
      ctx.fillRect(20, 20, 220, 46);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 20px system-ui';
      ctx.fillText('⚠️ انزل أكثر! (Go lower)', 32, 50);
    }

    ctx.restore();
  }, []);

  const saveCurrentSet = useCallback(async () => {
    const state = repStateRef.current;
    if (state.reps === 0 && state.errors.length === 0) return;
    if (!activeClient) {
      toast.error('اختر لاعباً لحفظ الجولة في سجله');
      return;
    }

    setSavingSet(true);
    const errors = Array.from(new Set(state.errors.map(errorType).filter((t): t is SquatErrorType => t !== null))).map((type) => ({ type }));
    try {
      await telegramApi.saveSquatCheck(activeClient.id, { reps: state.reps, errors, confidence: 1 });
      const info = `تم حفظ الجولة: ${state.reps} تكرار لـ ${activeClient.name}`;
      setLastSavedInfo(info);
      toast.success(info);
      onSetSaved?.(state.reps);
    } catch {
      toast.error('تعذر حفظ الجولة في سجل الفحص');
    } finally {
      setSavingSet(false);
    }
  }, [activeClient, onSetSaved]);

  const startCamera = useCallback(async () => {
    setStatus('loading');
    setErrorMsg('');
    try {
      await Promise.all([loadScript(CDN_POSE), loadScript(CDN_CAMERA), loadScript(CDN_DRAWING)]);

      if (!window.Pose || !window.Camera) throw new Error('تعذر تحميل مكتبات الرؤية الحاسوبية');

      const pose = new window.Pose({
        locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`,
      });
      pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });
      pose.onResults(handleResults);
      poseRef.current = pose;

      const video = videoRef.current!;
      const cam = new window.Camera(video, {
        onFrame: async () => {
          if (poseRef.current) await poseRef.current.send({ image: video });
        },
        width: 640,
        height: 480,
      });
      cameraRef.current = cam;
      await cam.start();
      setStatus('running');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'تعذر تشغيل الكاميرا';
      if (msg.toLowerCase().includes('permission') || msg.toLowerCase().includes('notallowed')) {
        setErrorMsg('تم رفض إذن الكاميرا. يرجى تفعيل إذن الكاميرا في المتصفح والمحاولة مجدداً.');
      } else {
        setErrorMsg(msg);
      }
      setStatus('error');
    }
  }, [handleResults]);

  const stopCamera = useCallback(async () => {
    await saveCurrentSet();
    cleanup();
    setStatus('idle');
    setReps(0);
    setKneeAngle(null);
    setGoLower(false);
    setCurrentPhase('standing');
    repStateRef.current = { reps: 0, phase: 'standing', touchedBottom: false, errors: [] };
  }, [cleanup, saveCurrentSet]);

  const phaseColors: Record<Phase, string> = {
    standing: 'text-good',
    descending: 'text-warn',
    bottom: 'text-primary',
    ascending: 'text-accent',
  };

  const phaseLabels: Record<Phase, string> = {
    standing: 'وضع الوقوف (>160°)',
    descending: 'نزول للسكوات',
    bottom: 'أقصى نزول (<100°) ✓',
    ascending: 'صعود للأعلى',
  };

  return (
    <Card className="flex flex-col overflow-hidden">
      <CardHeader
        title="فحص أداء السكوات الآلي"
        subtitle="تحليل مباشر لتكنيك الحركة بالذكاء الاصطناعي وعد التكرارات"
        icon={<Camera className="h-5 w-5" />}
        actions={
          <div className="flex items-center gap-2">
            {status === 'running' && (
              <Button
                variant="outline"
                size="sm"
                icon={<Save className="h-4 w-4" />}
                loading={savingSet}
                onClick={() => saveCurrentSet()}
              >
                حفظ الجولة
              </Button>
            )}
            {status === 'running' ? (
              <Button variant="danger" size="sm" onClick={stopCamera}>
                إيقاف وحفظ
              </Button>
            ) : (
              <Button size="sm" onClick={startCamera} loading={status === 'loading'}>
                {status === 'idle' ? 'تشغيل الكاميرا' : status === 'error' ? 'إعادة المحاولة' : 'جارٍ التشغيل…'}
              </Button>
            )}
          </div>
        }
      />

      {/* اختيار المشترك للجولة */}
      <div className="flex items-center justify-between gap-3 border-b border-line bg-surface-2 px-5 py-2.5 text-xs">
        <span className="font-semibold text-muted">المشترك لهذه الجولة:</span>
        <div className="flex gap-1.5">
          {players.data?.length === 0 && <span className="text-muted">أضف لاعباً أولاً</span>}
          {players.data?.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setActiveClientId(c.id)}
              className={`rounded-lg px-2.5 py-1 font-semibold transition ${
                activeClient?.id === c.id ? 'bg-primary text-on-primary' : 'bg-surface text-ink hover:bg-line/60'
              }`}
            >
              {c.name.split(' ')[0]}
            </button>
          ))}
        </div>
      </div>

      {/* شريط الإحصائيات الفوري */}
      <div className="flex flex-wrap items-center gap-6 border-b border-line px-5 py-3">
        {/* عداد التكرارات */}
        <div className="flex flex-col items-center min-w-[3.5rem]">
          <span className="num text-5xl font-black text-primary leading-none">{reps}</span>
          <span className="mt-1 text-xs font-semibold text-muted uppercase tracking-wide">تكرار</span>
        </div>

        <div className="h-10 w-px bg-line" />

        {/* زاوية الركبة */}
        <div className="flex flex-col items-center min-w-[4rem]">
          <span className="num text-3xl font-bold text-ink leading-none">
            {kneeAngle !== null ? `${kneeAngle}°` : '—'}
          </span>
          <span className="mt-1 text-xs font-semibold text-muted uppercase tracking-wide">زاوية الركبة</span>
        </div>

        <div className="h-10 w-px bg-line" />

        {/* حالة الحركة */}
        <div className="flex flex-col items-start">
          <span className={`text-sm font-bold ${status === 'running' ? phaseColors[currentPhase] : 'text-muted'}`}>
            {status === 'running' ? phaseLabels[currentPhase] : 'جاهز للبدء'}
          </span>
          <span className="mt-1 text-xs font-semibold text-muted uppercase tracking-wide">مرحلة الحركة</span>
        </div>

        {/* تنبيه العمق */}
        {goLower && (
          <div className="ms-auto flex items-center gap-2 rounded-xl bg-bad/15 border border-bad/30 px-3.5 py-2 animate-pulse">
            <ArrowDownCircle className="h-5 w-5 text-bad" />
            <span className="text-sm font-bold text-bad">انزل أكثر! (الورك أعلى من الركبة)</span>
          </div>
        )}

        {status === 'running' && !goLower && currentPhase === 'bottom' && (
          <div className="ms-auto flex items-center gap-2 rounded-xl bg-good/15 border border-good/30 px-3.5 py-2">
            <CheckCircle2 className="h-5 w-5 text-good" />
            <span className="text-sm font-bold text-good">عمق ممتاز! (&lt;100°)</span>
          </div>
        )}
      </div>

      {/* منطقة الكاميرا والرؤية الحاسوبية */}
      <div className="relative bg-zinc-950 aspect-video flex items-center justify-center overflow-hidden">
        <video ref={videoRef} className="hidden" playsInline muted />
        <canvas
          ref={canvasRef}
          width={640}
          height={480}
          className={`w-full h-full object-contain ${status === 'running' ? '' : 'hidden'}`}
        />

        {status === 'idle' && (
          <div className="flex flex-col items-center gap-3 py-12 text-center px-6 text-white">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/20 text-primary">
              <Camera className="h-8 w-8" />
            </div>
            <div>
              <p className="font-bold text-base">فاحص السكوات بالرؤية الحاسوبية جاهز</p>
              <p className="mt-1 text-xs text-zinc-400">اضغط "تشغيل الكاميرا" لبدء كشف المفاصل والعد التلقائي</p>
            </div>
            <div className="mt-2 text-xs text-zinc-300 text-start space-y-1 bg-white/5 p-3 rounded-xl border border-white/10">
              <p>• <strong>الوقوف:</strong> زاوية الركبة أعلى من 160°</p>
              <p>• <strong>أقصى نزول:</strong> زاوية الركبة أقل من 100° لاحتساب التكرار</p>
              <p>• <strong>العمق الصحيح:</strong> يظهر تنبيه "انزل أكثر" فوراً إذا ظل الورك أعلى من مستوى الركبة</p>
              <p>• <strong>الحفظ:</strong> تُسجل التكرارات والأخطاء في قاعدة البيانات</p>
            </div>
          </div>
        )}

        {status === 'loading' && (
          <div className="flex flex-col items-center gap-3 text-white">
            <RefreshCw className="h-10 w-10 animate-spin text-primary" />
            <p className="font-semibold text-sm">جارٍ تحميل نموذج الرؤية الحاسوبية…</p>
            <p className="text-xs text-zinc-400">طلب الإذن للوصول إلى الكاميرا</p>
          </div>
        )}

        {status === 'error' && (
          <div className="flex flex-col items-center gap-3 py-10 text-center px-6 text-white">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-bad/20 text-bad">
              <AlertTriangle className="h-7 w-7" />
            </div>
            <div>
              <p className="font-bold text-sm">تعذر تشغيل الكاميرا</p>
              <p className="mt-1 text-xs text-zinc-300 max-w-sm">{errorMsg}</p>
            </div>
            <Button size="sm" onClick={startCamera}>
              إعادة محاولة تشغيل الكاميرا
            </Button>
          </div>
        )}
      </div>

      {/* التذييل */}
      <div className="bg-surface-2 px-5 py-2 text-xs text-muted flex items-center justify-between">
        <span>معايير الحركة: وقوف &gt;160° · نزول كامل &lt;100°</span>
        {lastSavedInfo && (
          <Badge tone="good" className="truncate max-w-xs">{lastSavedInfo}</Badge>
        )}
      </div>
    </Card>
  );
}
