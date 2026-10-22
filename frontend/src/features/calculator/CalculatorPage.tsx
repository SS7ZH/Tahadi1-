import clsx from 'clsx';
import { FileDown, Flame, Info, Sigma, Target } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import type { MacroSettings, NutritionGoal, Sex } from '@/api/types';
import { MacroView } from '@/components/MacroView';
import { Badge, Button, Card, CardHeader, Input, PageHeader, Select } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { useLocation, useNavigate } from 'react-router-dom';
import { useActivityFactors, useNutritionSettings, useSummary } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { bmi, bmiLabel, bmrMifflin } from '@/lib/calc';
import { downloadPdf } from '@/lib/download';
import { buildPlan, DEFAULT_SETTINGS, GOAL_MAP } from '@/lib/nutrition';
import { fmtInt, fmtNumber } from '@/lib/format';
import { ExportCalculatorModal } from './ExportCalculatorModal';

const LIMITS = { age: [10, 100], weight: [20, 300], height: [100, 250] } as const;

function parse(v: string, [lo, hi]: readonly [number, number]) {
  if (v.trim() === '') return { value: null, error: undefined };
  const n = Number(v);
  if (Number.isNaN(n) || n < lo || n > hi) return { value: null, error: `${tr.calculator.outOfRange} (${lo}–${hi})` };
  return { value: n, error: undefined };
}

export function CalculatorPage() {
  // Public page: `user` is null for visitors (PDF export then asks them to log in).
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const factors = useActivityFactors();
  const nutritionSettings = useNutritionSettings();
  const isClient = user?.role === 'client';
  const summary = useSummary(user?.id ?? 0, isClient);

  const [sex, setSex] = useState<Sex>('male');
  const [age, setAge] = useState('');
  const [weight, setWeight] = useState('');
  const [height, setHeight] = useState('');
  const [activity, setActivity] = useState('moderate');
  const [goal, setGoal] = useState<NutritionGoal>('maintenance');
  const [prefilled, setPrefilled] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  // Players get their own data pre-filled.
  useEffect(() => {
    if (!user || !isClient || prefilled || !user.profile) return;
    const p = user.profile;
    setSex(p.sex);
    if (user.age != null) setAge(String(user.age));
    if (p.height_cm) setHeight(String(p.height_cm));
    if (p.activity_key) setActivity(p.activity_key);
    setGoal(GOAL_MAP[p.goal]);
    const w = summary.data?.results.weight;
    if (w) setWeight(String(w));
    if (summary.data || summary.isError) setPrefilled(true);
  }, [isClient, prefilled, user, summary.data, summary.isError]);

  const a = parse(age, LIMITS.age);
  const w = parse(weight, LIMITS.weight);
  const h = parse(height, LIMITS.height);
  const factor = factors.data?.find((f) => f.key === activity);
  const settings = useMemo(() => {
    const out: Record<NutritionGoal, MacroSettings> = { ...DEFAULT_SETTINGS };
    nutritionSettings.data?.forEach((r) => (out[r.goal] = r));
    return out;
  }, [nutritionSettings.data]);

  const result = useMemo(() => {
    if (a.value === null || w.value === null || h.value === null || !factor) return null;
    const bmr = bmrMifflin(sex, w.value, h.value, a.value);
    const tdee = bmr * factor.factor;
    const b = bmi(w.value, h.value);
    return { bmr, tdee, plan: buildPlan(tdee, settings[goal]), bmi: b };
  }, [a.value, w.value, h.value, factor, sex, settings, goal]);

  const runExport = async (names?: { clientId?: number; clientName?: string; coachName?: string }) => {
    if (a.value === null || w.value === null || h.value === null || !factor) return;
    setExporting(true);
    try {
      await downloadPdf('/pdf/calculator', {
        method: 'POST',
        body: {
          sex,
          age: a.value,
          weight: w.value,
          height: h.value,
          activity_key: activity,
          goal,
          meals_per_day: result?.plan?.meals_per_day,
          client_id: names?.clientId,
          client_name: names?.clientName,
          coach_name: names?.coachName,
        },
      });
      toast.success(tr.pdf.exported);
      setModalOpen(false);
    } catch (err) {
      toast.error(errorMessage(err) || tr.pdf.exportFailed);
    } finally {
      setExporting(false);
    }
  };

  const handleExportClick = () => {
    if (!user) {
      toast.info(tr.calculator.loginToExport);
      navigate('/login', { state: { from: location.pathname } });
      return;
    }
    if (isClient) {
      runExport();
    } else {
      setModalOpen(true);
    }
  };

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title={tr.calculator.title} subtitle={tr.calculator.subtitle} />
      <div className="grid gap-4 lg:grid-cols-[1fr_1.1fr]">
        <Card className="p-4 sm:p-5">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <span className="mb-1.5 block text-sm font-medium">{tr.calculator.sex}</span>
              <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label={tr.calculator.sex}>
                {(['male', 'female'] as Sex[]).map((s) => (
                  <button
                    key={s}
                    type="button"
                    role="radio"
                    aria-checked={sex === s}
                    onClick={() => setSex(s)}
                    className={clsx(
                      'rounded-xl border px-3 py-2.5 text-sm font-semibold transition',
                      sex === s ? 'border-primary bg-primary/10 text-primary' : 'border-line hover:bg-surface-2',
                    )}
                  >
                    {tr.sex[s]}
                  </button>
                ))}
              </div>
            </div>
            <Input label={tr.calculator.age} type="number" inputMode="numeric" dir="ltr" value={age} onChange={(e) => setAge(e.target.value)} error={a.error} />
            <Input label={tr.calculator.weight} type="number" step="any" inputMode="decimal" dir="ltr" value={weight} onChange={(e) => setWeight(e.target.value)} error={w.error} />
            <Input label={tr.calculator.height} type="number" step="any" inputMode="decimal" dir="ltr" value={height} onChange={(e) => setHeight(e.target.value)} error={h.error} wrapperClassName="col-span-2 sm:col-span-1" />
            <Select label={tr.calculator.activity} value={activity} onChange={(e) => setActivity(e.target.value)} wrapperClassName="col-span-2">
              {factors.data?.map((f) => (
                <option key={f.key} value={f.key}>
                  {loc(f.name_ar, f.name_en)} — {loc(f.description_ar, f.description_en)} (×{f.factor})
                </option>
              ))}
            </Select>
          </div>
          {isClient && prefilled && <p className="mt-3 text-xs text-muted">{tr.calculator.prefilled}</p>}
        </Card>

        <div className="flex flex-col gap-4">
          {result ? (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Card className="p-4">
                  <p className="text-xs font-medium text-muted">{tr.calculator.bmr}</p>
                  <p className="mt-2 text-3xl font-bold">
                    <span className="num">{fmtInt(result.bmr)}</span>
                  </p>
                  <p className="mt-1 text-xs text-muted">{tr.common.kcalPerDay}</p>
                  <p className="mt-2 text-[11px] leading-relaxed text-muted">{tr.calculator.bmrHint}</p>
                </Card>
                <Card className="border-primary/40 bg-primary/5 p-4">
                  <p className="text-xs font-medium text-muted">{tr.calculator.tdee}</p>
                  <p className="mt-2 text-3xl font-bold text-primary">
                    <span className="num">{fmtInt(result.tdee)}</span>
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    {tr.common.kcalPerDay} · <span className="num">×{factor?.factor}</span>
                  </p>
                  <p className="mt-2 text-[11px] leading-relaxed text-muted">{tr.calculator.tdeeHint}</p>
                </Card>
              </div>
              <Card>
                <CardHeader
                  title={tr.calculator.targets}
                  icon={<Target className="h-5 w-5" />}
                  actions={
                    <Button
                      variant="outline"
                      size="sm"
                      icon={<FileDown className="h-4 w-4" />}
                      loading={exporting && isClient}
                      onClick={handleExportClick}
                    >
                      {tr.pdf.exportPdf}
                    </Button>
                  }
                />
                <ul className="divide-y divide-line px-4 sm:px-5">
                  {(['maintenance', 'weight_loss', 'weight_gain'] as NutritionGoal[]).map((g) => ({
                    label: tr.nutritionGoals[g],
                    hint: tr.calculator.delta(settings[g].calorie_adjustment),
                    value: result.tdee + settings[g].calorie_adjustment,
                    tone: g === 'weight_loss' ? 'text-accent' : g === 'weight_gain' ? 'text-primary' : 'text-ink',
                  })).map((t) => (
                    <li key={t.label} className="flex items-center justify-between py-3">
                      <div>
                        <p className="text-sm font-semibold">{t.label}</p>
                        <p className="num text-start text-[11px] text-muted">{t.hint}</p>
                      </div>
                      <p className={clsx('text-lg font-bold', t.tone)}>
                        <span className="num">{fmtInt(t.value)}</span> <span className="text-xs font-normal text-muted">{tr.common.kcal}</span>
                      </p>
                    </li>
                  ))}
                </ul>
                <div className="flex flex-wrap items-center gap-2 border-t border-line px-4 py-3 text-xs text-muted sm:px-5">
                  <Info className="h-3.5 w-3.5" />
                  {tr.calculator.targetsNote}
                  <span className="ms-auto">
                    {tr.summary.bmi}: <b className="num text-ink">{fmtNumber(result.bmi, 1)}</b> <Badge>{bmiLabel(result.bmi)}</Badge>
                  </span>
                </div>
              </Card>
              <Card>
                <CardHeader title={tr.calculator.macrosTitle} icon={<Flame className="h-5 w-5" />} />
                <div className="flex flex-col gap-4 p-4 sm:p-5">
                  <Select label={tr.calculator.goal} value={goal} onChange={(e) => setGoal(e.target.value as NutritionGoal)}>
                    {(['weight_loss', 'maintenance', 'weight_gain'] as NutritionGoal[]).map((g) => (
                      <option key={g} value={g}>
                        {tr.nutritionGoals[g]} ({tr.calculator.delta(settings[g].calorie_adjustment)})
                      </option>
                    ))}
                  </Select>
                  <MacroView numbers={result.plan} />
                </div>
              </Card>
            </>
          ) : (
            <Card className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <Flame className="h-7 w-7" />
              </span>
              <p className="text-sm text-muted">{tr.calculator.fillAll}</p>
            </Card>
          )}
        </div>

        <Card className="lg:col-span-2">
          <CardHeader title={tr.calculator.formulas} icon={<Sigma className="h-5 w-5" />} />
          <div className="flex flex-col gap-2 p-4 text-sm leading-loose sm:p-5">
            <p className="rounded-xl bg-surface-2 px-3 py-2">{tr.calculator.menFormula}</p>
            <p className="rounded-xl bg-surface-2 px-3 py-2">{tr.calculator.womenFormula}</p>
            <p className="rounded-xl bg-surface-2 px-3 py-2">{tr.calculator.tdeeFormula}</p>
          </div>
        </Card>
      </div>

      <ExportCalculatorModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        userRole={user?.role ?? 'client'}
        exporting={exporting}
        onExport={runExport}
      />
    </div>
  );
}
