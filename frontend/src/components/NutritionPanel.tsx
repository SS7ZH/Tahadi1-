import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, History, Info, Salad, SlidersHorizontal } from 'lucide-react';
import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { nutritionApi } from '@/api/endpoints';
import { MACROS, type Goal, type Macro, type NutritionOverview, type NutritionPlanInput } from '@/api/types';
import { useNutrition, useNutritionHistory } from '@/hooks/queries';
import { tr } from '@/i18n';
import { fmtDateTime, fmtInt } from '@/lib/format';
import { buildPlan, DEFAULT_SETTINGS, GOAL_MAP } from '@/lib/nutrition';
import { MacroView } from './MacroView';
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, Input, Select, Skeleton, Textarea } from './ui';

const GOALS: Goal[] = ['fat_loss', 'fitness', 'health', 'performance', 'muscle_gain'];
const num = (s: string) => (s.trim() === '' ? null : Number(s));

function MissingBasis({ data }: { data: NutritionOverview }) {
  const missing = data.basis?.missing ?? [];
  if (!missing.length) return null;
  return (
    <div className="flex gap-2 rounded-xl bg-surface-2 px-3 py-2.5 text-sm">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted" />
      <p>
        {tr.nutrition.missing}
        {missing.map((m) => tr.nutrition.missingLabels[m] ?? m).join('، ')}. {tr.nutrition.manualOnly}
      </p>
    </div>
  );
}

function HistoryList({ clientId }: { clientId: number }) {
  const history = useNutritionHistory(clientId);
  if (history.isLoading) return <Skeleton className="m-4 h-24" />;
  if (!history.data?.length) return <p className="p-4 text-sm text-muted">{tr.nutrition.noHistory}</p>;
  return (
    <ul className="divide-y divide-line">
      {history.data.map((p, i) => (
        <li key={p.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm sm:px-5">
          <span className="w-full text-[11px] text-muted sm:w-40">
            {fmtDateTime(p.created_at)}
            {p.created_by_name && ` · ${p.created_by_name}`}
          </span>
          <span className="font-bold">
            <span className="num">{fmtInt(p.calories)}</span> {tr.common.kcal}
          </span>
          <span className="text-muted">
            {MACROS.map((m) => (
              <span key={m} className="me-2">
                {tr.macros[m]} <span className="num font-semibold text-ink">{p.grams[m]}</span>
                {tr.nutrition.grams}
              </span>
            ))}
          </span>
          <span className="text-muted">
            {tr.nutritionGoals[p.nutrition_goal]} · <span className="num">{p.meals_per_day}</span> × 🍽
          </span>
          {i === 0 && <Badge tone="good">{tr.nutrition.saved}</Badge>}
          {p.overridden.length > 0 && <Badge tone="warn">{tr.nutrition.adjusted}</Badge>}
          {p.note && <p className="w-full text-xs text-ink/70">{p.note}</p>}
        </li>
      ))}
    </ul>
  );
}

export function NutritionPanel({ clientId }: { clientId: number }) {
  const qc = useQueryClient();
  const { data, isLoading, error, refetch } = useNutrition(clientId);
  const [goal, setGoal] = useState<Goal | null>(null);
  const [form, setForm] = useState({ calories: '', protein: '', carbs: '', fat: '', meals: '', note: '' });
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const activeGoal: Goal = goal ?? data?.goal ?? 'fitness';
  const ngoal = GOAL_MAP[activeGoal];
  const settings = data?.settings?.[ngoal] ?? DEFAULT_SETTINGS[ngoal];
  const dcn = data?.basis?.dcn ?? null;

  // Suggested values for the goal selected in the form, and a live preview with the coach's overrides.
  const suggestion = useMemo(() => (dcn != null ? buildPlan(dcn, settings) : null), [dcn, settings]);
  const preview = useMemo(() => {
    const calories = num(form.calories);
    const base = dcn ?? (calories != null ? calories - settings.calorie_adjustment : null);
    if (base == null) return null;
    const grams = Object.fromEntries(MACROS.map((m) => [m, num(form[m])])) as Record<Macro, number | null>;
    return buildPlan(base, settings, { calories, grams, meals: num(form.meals) });
  }, [dcn, settings, form]);

  const save = useMutation({
    mutationFn: (body: NutritionPlanInput) => nutritionApi.save(clientId, body),
    onSuccess: async () => {
      toast.success(tr.nutrition.savedToast);
      setForm({ calories: '', protein: '', carbs: '', fat: '', meals: '', note: '' });
      setGoal(null);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['client', clientId] }),
        qc.invalidateQueries({ queryKey: ['clients'] }),
      ]);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  if (isLoading) return <Skeleton className="h-96" />;
  if (error || !data) return <ErrorState message={errorMessage(error)} onRetry={() => refetch()} />;

  const goalChanged = goal !== null && goal !== data.goal;
  const submit = (withOverrides: boolean) =>
    save.mutate({
      goal: goalChanged ? activeGoal : undefined,
      ...(withOverrides
        ? {
            calories: num(form.calories),
            protein_g: num(form.protein),
            carbs_g: num(form.carbs),
            fat_g: num(form.fat),
            meals_per_day: num(form.meals),
          }
        : {}),
      note: form.note.trim() || null,
    });

  return (
    <div className="flex flex-col gap-4">
      {data.suggestion_changed && data.current && (
        <div className="flex flex-col gap-3 rounded-2xl border border-warn/40 bg-warn/10 p-4 sm:flex-row sm:items-center">
          <AlertTriangle className="h-5 w-5 shrink-0 text-warn" />
          <p className="flex-1 text-sm">{tr.nutrition.changed}</p>
          <Button size="sm" onClick={() => submit(false)} loading={save.isPending}>
            {tr.nutrition.applyNew}
          </Button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            title={tr.nutrition.suggested}
            subtitle={
              data.basis?.weight != null && data.basis.dcn != null
                ? `${tr.nutrition.basis(data.basis.weight)} · ${tr.nutrition.dcn}: ${fmtInt(data.basis.dcn)}`
                : undefined
            }
            icon={<Salad className="h-5 w-5" />}
          />
          <div className="flex flex-col gap-4 p-4 sm:p-5">
            <Select
              label={tr.nutrition.goal}
              hint={tr.nutrition.goalHint}
              value={activeGoal}
              onChange={(e) => setGoal(e.target.value as Goal)}
            >
              {GOALS.map((g) => (
                <option key={g} value={g}>
                  {tr.goals[g]} → {tr.nutritionGoals[GOAL_MAP[g]]}
                </option>
              ))}
            </Select>
            <MissingBasis data={data} />
            {suggestion && <MacroView numbers={suggestion} />}
            {suggestion && (
              <Button icon={<CheckCircle2 className="h-4 w-4" />} onClick={() => submit(false)} loading={save.isPending}>
                {tr.nutrition.accept}
              </Button>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title={tr.nutrition.saved}
            subtitle={data.current ? `${tr.nutrition.updatedBy}: ${fmtDateTime(data.current.created_at)}` : undefined}
            icon={<CheckCircle2 className="h-5 w-5" />}
            actions={data.current && data.current.overridden.length > 0 ? <Badge tone="warn">{tr.nutrition.adjusted}</Badge> : undefined}
          />
          <div className="p-4 sm:p-5">
            {data.current ? (
              <>
                <p className="mb-3 text-sm text-muted">
                  {tr.nutritionGoals[data.current.nutrition_goal]} ·{' '}
                  <b className="num text-ink">{fmtInt(data.current.calories)}</b> {tr.common.kcalPerDay}
                </p>
                <MacroView numbers={data.current} />
                {data.current.note && <p className="mt-3 rounded-xl bg-surface-2 px-3 py-2 text-sm">{data.current.note}</p>}
              </>
            ) : (
              <EmptyState title={tr.nutrition.noHistory} />
            )}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title={tr.nutrition.adjust} subtitle={tr.nutrition.adjustHint} icon={<SlidersHorizontal className="h-5 w-5" />} />
        <form
          className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[1fr_1fr]"
          onSubmit={(e) => {
            e.preventDefault();
            submit(true);
          }}
        >
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Input
              label={tr.nutrition.calories}
              type="number"
              inputMode="numeric"
              dir="ltr"
              placeholder={suggestion ? String(suggestion.calories) : ''}
              value={form.calories}
              onChange={(e) => set('calories', e.target.value)}
              suffix={tr.common.kcal}
              wrapperClassName="col-span-2 sm:col-span-1"
            />
            {MACROS.map((m) => (
              <Input
                key={m}
                label={tr.macros[m]}
                type="number"
                inputMode="numeric"
                dir="ltr"
                placeholder={preview ? String(preview.grams[m]) : ''}
                value={form[m]}
                onChange={(e) => set(m, e.target.value)}
                suffix={tr.nutrition.grams}
              />
            ))}
            <Select
              label={tr.nutrition.mealsPerDay}
              hint={tr.nutrition.mealsRange(settings.meals_min, settings.meals_max)}
              value={form.meals}
              onChange={(e) => set('meals', e.target.value)}
            >
              <option value="">{settings.meals_min}</option>
              {Array.from({ length: settings.meals_max - settings.meals_min }, (_, i) => settings.meals_min + i + 1).map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </Select>
            <Textarea
              label={tr.nutrition.note}
              rows={2}
              value={form.note}
              onChange={(e) => set('note', e.target.value)}
              wrapperClassName="col-span-2 sm:col-span-3"
              maxLength={2000}
            />
          </div>
          <div className="flex flex-col gap-3">
            {preview ? <MacroView numbers={preview} compareTo={suggestion} /> : <MissingBasis data={data} />}
            <Button type="submit" loading={save.isPending} disabled={!preview} className="self-start">
              {tr.nutrition.savePlan}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardHeader title={tr.nutrition.history} icon={<History className="h-5 w-5" />} />
        <HistoryList clientId={clientId} />
      </Card>
    </div>
  );
}
