import clsx from 'clsx';
import { Flame, Info, Sigma, Target } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { Sex } from '@/api/types';
import { Badge, Card, CardHeader, Input, PageHeader, Select } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { useActivityFactors, useSummary } from '@/hooks/queries';
import { ar } from '@/i18n/ar';
import { bmi, bmiLabel, bmrMifflin, calorieTargets } from '@/lib/calc';
import { fmtInt, fmtNumber } from '@/lib/format';

const LIMITS = { age: [10, 100], weight: [20, 300], height: [100, 250] } as const;

function parse(v: string, [lo, hi]: readonly [number, number]) {
  if (v.trim() === '') return { value: null, error: undefined };
  const n = Number(v);
  if (Number.isNaN(n) || n < lo || n > hi) return { value: null, error: `${ar.calculator.outOfRange} (${lo}–${hi})` };
  return { value: n, error: undefined };
}

export function CalculatorPage() {
  const user = useCurrentUser();
  const factors = useActivityFactors();
  const isClient = user.role === 'client';
  const summary = useSummary(user.id, isClient);

  const [sex, setSex] = useState<Sex>('male');
  const [age, setAge] = useState('');
  const [weight, setWeight] = useState('');
  const [height, setHeight] = useState('');
  const [activity, setActivity] = useState('moderate');
  const [prefilled, setPrefilled] = useState(false);

  // Players get their own data pre-filled.
  useEffect(() => {
    if (!isClient || prefilled || !user.profile) return;
    const p = user.profile;
    setSex(p.sex);
    if (user.age != null) setAge(String(user.age));
    if (p.height_cm) setHeight(String(p.height_cm));
    if (p.activity_key) setActivity(p.activity_key);
    const w = summary.data?.results.weight;
    if (w) setWeight(String(w));
    if (summary.data || summary.isError) setPrefilled(true);
  }, [isClient, prefilled, user, summary.data, summary.isError]);

  const a = parse(age, LIMITS.age);
  const w = parse(weight, LIMITS.weight);
  const h = parse(height, LIMITS.height);
  const factor = factors.data?.find((f) => f.key === activity);

  const result = useMemo(() => {
    if (a.value === null || w.value === null || h.value === null || !factor) return null;
    const bmr = bmrMifflin(sex, w.value, h.value, a.value);
    const tdee = bmr * factor.factor;
    const b = bmi(w.value, h.value);
    return { bmr, tdee, targets: calorieTargets(tdee), bmi: b };
  }, [a.value, w.value, h.value, factor, sex]);

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title={ar.calculator.title} subtitle={ar.calculator.subtitle} />
      <div className="grid gap-4 lg:grid-cols-[1fr_1.1fr]">
        <Card className="p-4 sm:p-5">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <span className="mb-1.5 block text-sm font-medium">{ar.calculator.sex}</span>
              <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label={ar.calculator.sex}>
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
                    {ar.sex[s]}
                  </button>
                ))}
              </div>
            </div>
            <Input label={ar.calculator.age} type="number" inputMode="numeric" dir="ltr" value={age} onChange={(e) => setAge(e.target.value)} error={a.error} />
            <Input label={ar.calculator.weight} type="number" step="any" inputMode="decimal" dir="ltr" value={weight} onChange={(e) => setWeight(e.target.value)} error={w.error} />
            <Input label={ar.calculator.height} type="number" step="any" inputMode="decimal" dir="ltr" value={height} onChange={(e) => setHeight(e.target.value)} error={h.error} wrapperClassName="col-span-2 sm:col-span-1" />
            <Select label={ar.calculator.activity} value={activity} onChange={(e) => setActivity(e.target.value)} wrapperClassName="col-span-2">
              {factors.data?.map((f) => (
                <option key={f.key} value={f.key}>
                  {f.name_ar} — {f.description_ar} (×{f.factor})
                </option>
              ))}
            </Select>
          </div>
          {isClient && prefilled && <p className="mt-3 text-xs text-muted">{ar.calculator.prefilled}</p>}
        </Card>

        <div className="flex flex-col gap-4">
          {result ? (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Card className="p-4">
                  <p className="text-xs font-medium text-muted">{ar.calculator.bmr}</p>
                  <p className="mt-2 text-3xl font-bold">
                    <span className="num">{fmtInt(result.bmr)}</span>
                  </p>
                  <p className="mt-1 text-xs text-muted">{ar.common.kcalPerDay}</p>
                  <p className="mt-2 text-[11px] leading-relaxed text-muted">{ar.calculator.bmrHint}</p>
                </Card>
                <Card className="border-primary/40 bg-primary/5 p-4">
                  <p className="text-xs font-medium text-muted">{ar.calculator.tdee}</p>
                  <p className="mt-2 text-3xl font-bold text-primary">
                    <span className="num">{fmtInt(result.tdee)}</span>
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    {ar.common.kcalPerDay} · <span className="num">×{factor?.factor}</span>
                  </p>
                  <p className="mt-2 text-[11px] leading-relaxed text-muted">{ar.calculator.tdeeHint}</p>
                </Card>
              </div>
              <Card>
                <CardHeader title={ar.calculator.targets} icon={<Target className="h-5 w-5" />} />
                <ul className="divide-y divide-line px-4 sm:px-5">
                  {[
                    { label: ar.calculator.maintenance, hint: 'TDEE', value: result.targets.maintenance, tone: 'text-ink' },
                    { label: ar.calculator.fatLoss, hint: ar.calculator.fatLossHint, value: result.targets.fat_loss, tone: 'text-accent' },
                    { label: ar.calculator.muscleGain, hint: ar.calculator.muscleGainHint, value: result.targets.muscle_gain, tone: 'text-primary' },
                  ].map((t) => (
                    <li key={t.label} className="flex items-center justify-between py-3">
                      <div>
                        <p className="text-sm font-semibold">{t.label}</p>
                        <p className="num text-start text-[11px] text-muted">{t.hint}</p>
                      </div>
                      <p className={clsx('text-lg font-bold', t.tone)}>
                        <span className="num">{fmtInt(t.value)}</span> <span className="text-xs font-normal text-muted">{ar.common.kcal}</span>
                      </p>
                    </li>
                  ))}
                </ul>
                <div className="flex flex-wrap items-center gap-2 border-t border-line px-4 py-3 text-xs text-muted sm:px-5">
                  <Info className="h-3.5 w-3.5" />
                  {ar.calculator.targetsNote}
                  <span className="ms-auto">
                    {ar.summary.bmi}: <b className="num text-ink">{fmtNumber(result.bmi, 1)}</b> <Badge>{bmiLabel(result.bmi)}</Badge>
                  </span>
                </div>
              </Card>
            </>
          ) : (
            <Card className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <Flame className="h-7 w-7" />
              </span>
              <p className="text-sm text-muted">{ar.calculator.fillAll}</p>
            </Card>
          )}
        </div>

        <Card className="lg:col-span-2">
          <CardHeader title={ar.calculator.formulas} icon={<Sigma className="h-5 w-5" />} />
          <div className="flex flex-col gap-2 p-4 text-sm leading-loose sm:p-5">
            <p className="rounded-xl bg-surface-2 px-3 py-2">{ar.calculator.menFormula}</p>
            <p className="rounded-xl bg-surface-2 px-3 py-2">{ar.calculator.womenFormula}</p>
            <p className="rounded-xl bg-surface-2 px-3 py-2">{ar.calculator.tdeeFormula}</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
