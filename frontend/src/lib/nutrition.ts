/**
 * Client-side mirror of backend/app/services/nutrition.py (live previews and the calculator).
 * Saved plans always come from the server.
 */
import type { Goal, Macro, MacroSettings, NutritionGoal, NutritionNumbers } from '@/api/types';
import { MACROS } from '@/api/types';

export const KCAL_PER_G: Record<Macro, number> = { protein: 4, carbs: 4, fat: 9 };

export const GOAL_MAP: Record<Goal, NutritionGoal> = {
  fat_loss: 'weight_loss',
  muscle_gain: 'weight_gain',
  fitness: 'maintenance',
  health: 'maintenance',
  performance: 'maintenance',
};

export const DEFAULT_SETTINGS: Record<NutritionGoal, MacroSettings> = {
  weight_loss: { calorie_adjustment: -500, protein_pct: 25, carbs_pct: 50, fat_pct: 25, meals_min: 4, meals_max: 5 },
  maintenance: { calorie_adjustment: 0, protein_pct: 20, carbs_pct: 55, fat_pct: 25, meals_min: 4, meals_max: 5 },
  weight_gain: { calorie_adjustment: 500, protein_pct: 15, carbs_pct: 60, fat_pct: 25, meals_min: 5, meals_max: 6 },
};

export const roundHalfUp = (x: number) => Math.floor(x + 0.5);

export function buildPlan(
  dcn: number,
  s: MacroSettings,
  opts: { calories?: number | null; grams?: Partial<Record<Macro, number | null>>; meals?: number | null } = {},
): NutritionNumbers & { suggested_calories: number } {
  const suggested = roundHalfUp(dcn + s.calorie_adjustment);
  const calories = opts.calories ?? suggested;
  const percentages = { protein: s.protein_pct, carbs: s.carbs_pct, fat: s.fat_pct };
  const grams = {} as Record<Macro, number>;
  for (const m of MACROS) {
    const o = opts.grams?.[m];
    grams[m] = o ?? roundHalfUp((calories * percentages[m]) / 100 / KCAL_PER_G[m]);
  }
  const meals = opts.meals ?? s.meals_min;
  const macros = {} as NutritionNumbers['macros'];
  for (const m of MACROS) {
    if (opts.grams?.[m] != null) {
      // coach-overridden grams: kcal and % follow from the grams
      const kcal = grams[m] * KCAL_PER_G[m];
      macros[m] = { g: grams[m], kcal, pct: calories ? Math.round((kcal / calories) * 1000) / 10 : 0 };
    } else {
      macros[m] = { g: grams[m], kcal: roundHalfUp((calories * percentages[m]) / 100), pct: percentages[m] };
    }
  }
  return {
    suggested_calories: suggested,
    calories,
    percentages,
    grams,
    macros,
    meals_per_day: meals,
    per_meal: {
      calories: roundHalfUp(calories / meals),
      protein: roundHalfUp(grams.protein / meals),
      carbs: roundHalfUp(grams.carbs / meals),
      fat: roundHalfUp(grams.fat / meals),
    },
    overridden: [],
  };
}
