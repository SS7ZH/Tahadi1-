import clsx from 'clsx';
import { Clock, Utensils } from 'lucide-react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { MACROS, type Macro, type NutritionNumbers } from '@/api/types';
import { useChartColors } from '@/hooks/useTheme';
import { tr } from '@/i18n';
import { fmtInt } from '@/lib/format';

const MACRO_TONE: Record<Macro, string> = {
  protein: 'bg-accent/10 text-accent',
  carbs: 'bg-primary/10 text-primary',
  fat: 'bg-warn/15 text-warn',
};

export function MacroSplitChart({ numbers, size = 168 }: { numbers: NutritionNumbers; size?: number }) {
  const colors = useChartColors();
  const fill: Record<Macro, string> = { protein: colors.accent, carbs: colors.primary, fat: colors.warn };
  const data = MACROS.map((m) => ({ key: m, name: tr.macros[m], value: numbers.macros[m].kcal }));
  return (
    <div style={{ width: size, height: size }} className="relative shrink-0" role="img" aria-label={tr.nutrition.split}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="100%" paddingAngle={2} stroke="none" isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.key} fill={fill[d.key]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(v: number, name: string) => [`${fmtInt(v)} ${tr.common.kcal}`, name]}
            contentStyle={{ background: colors.surface, border: `1px solid ${colors.line}`, borderRadius: 12, color: colors.ink, fontFamily: 'inherit' }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="num text-xl font-bold leading-none">{fmtInt(numbers.calories)}</span>
        <span className="mt-1 text-[11px] text-muted">{tr.common.kcalPerDay}</span>
      </div>
    </div>
  );
}

/** Read-only calories / macros / meals display. `compareTo` shows the suggested value under each number. */
export function MacroView({
  numbers,
  compareTo,
  showMeals = true,
  className,
}: {
  numbers: NutritionNumbers;
  compareTo?: NutritionNumbers | null;
  showMeals?: boolean;
  className?: string;
}) {
  const diff = (a: number, b?: number) => compareTo && b !== undefined && a !== b;
  return (
    <div className={clsx('flex flex-col gap-4', className)}>
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center">
        <MacroSplitChart numbers={numbers} />
        <div className="grid w-full flex-1 grid-cols-3 gap-2">
          {MACROS.map((m) => {
            const line = numbers.macros[m];
            return (
              <div key={m} className={clsx('rounded-xl px-3 py-2.5', MACRO_TONE[m])}>
                <p className="text-[11px] font-semibold">{tr.macros[m]}</p>
                <p className="mt-1 text-lg font-bold leading-none text-ink">
                  <span className="num">{fmtInt(line.g)}</span>
                  <span className="ms-0.5 text-xs font-normal text-muted">{tr.nutrition.grams}</span>
                </p>
                <p className="mt-1 text-[11px] text-muted">
                  <span className="num">{fmtInt(line.kcal)}</span> {tr.common.kcal} · <span className="num">{line.pct}%</span>
                </p>
                {diff(line.g, compareTo?.macros[m].g) && (
                  <p className="mt-1 text-[10px] text-muted">
                    {tr.nutrition.vsSuggested}: <span className="num">{compareTo!.macros[m].g}</span>
                    {tr.nutrition.grams}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {showMeals && (
        <div className="rounded-xl border border-line">
          <div className="flex items-center justify-between gap-2 border-b border-line px-3 py-2.5">
            <span className="flex items-center gap-1.5 text-sm font-semibold">
              <Utensils className="h-4 w-4 text-primary" />
              {tr.nutrition.mealsPerDay}
            </span>
            <span className="num text-lg font-bold">{numbers.meals_per_day}</span>
          </div>
          <div className="grid grid-cols-4 gap-1 px-3 py-2.5 text-center">
            <div>
              <p className="text-[11px] text-muted">{tr.common.kcal}</p>
              <p className="num font-semibold">{fmtInt(numbers.per_meal.calories)}</p>
            </div>
            {MACROS.map((m) => (
              <div key={m}>
                <p className="text-[11px] text-muted">{tr.macros[m]}</p>
                <p className="font-semibold">
                  <span className="num">{fmtInt(numbers.per_meal[m])}</span>
                  <span className="text-[11px] font-normal text-muted">{tr.nutrition.grams}</span>
                </p>
              </div>
            ))}
          </div>
          <p className="border-t border-line px-3 py-2 text-[11px] text-muted">
            {tr.nutrition.perMeal} · <Clock className="inline h-3 w-3" /> {tr.nutrition.tip}
          </p>
        </div>
      )}
    </div>
  );
}
