import { useMutation, useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';
import { Salad, Save } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { nutritionApi } from '@/api/endpoints';
import type { NutritionSettingRow } from '@/api/types';
import { Button, Card, CardHeader, ErrorState, Input, Skeleton } from '@/components/ui';
import { qk, useNutritionSettings } from '@/hooks/queries';
import { tr } from '@/i18n';

const FIELDS = ['calorie_adjustment', 'protein_pct', 'carbs_pct', 'fat_pct', 'meals_min', 'meals_max'] as const;
type Field = (typeof FIELDS)[number];

function Row({ row }: { row: NutritionSettingRow }) {
  const qc = useQueryClient();
  const [v, setV] = useState<Record<Field, string>>(
    Object.fromEntries(FIELDS.map((f) => [f, String(row[f])])) as Record<Field, string>,
  );
  const total = Number(v.protein_pct) + Number(v.carbs_pct) + Number(v.fat_pct);
  const dirty = FIELDS.some((f) => v[f] !== String(row[f]));
  const valid = Math.abs(total - 100) < 0.01 && Number(v.meals_min) <= Number(v.meals_max);

  const save = useMutation({
    mutationFn: () =>
      nutritionApi.updateSetting(row.id, Object.fromEntries(FIELDS.map((f) => [f, Number(v[f])])) as Partial<NutritionSettingRow>),
    onSuccess: async () => {
      toast.success(tr.admin.nutritionSaved);
      await Promise.all([qc.invalidateQueries({ queryKey: qk.nutritionSettings }), qc.invalidateQueries({ queryKey: ['client'] })]);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const label: Record<Field, string> = {
    calorie_adjustment: tr.admin.calorieAdjustment,
    protein_pct: `${tr.macros.protein} %`,
    carbs_pct: `${tr.macros.carbs} %`,
    fat_pct: `${tr.macros.fat} %`,
    meals_min: tr.admin.mealsMin,
    meals_max: tr.admin.mealsMax,
  };

  return (
    <li className="px-4 py-3 sm:px-5">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="font-bold">{tr.nutritionGoals[row.goal]}</span>
        <span className={clsx('num text-xs font-semibold', valid ? 'text-good' : 'text-bad')}>{tr.admin.percentTotal(total)}</span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-[repeat(6,minmax(0,1fr))_auto] lg:items-end">
        {FIELDS.map((f) => (
          <Input
            key={f}
            label={label[f]}
            type="number"
            dir="ltr"
            step={f.endsWith('pct') ? '0.5' : '1'}
            value={v[f]}
            onChange={(e) => setV((s) => ({ ...s, [f]: e.target.value }))}
          />
        ))}
        <Button
          className="col-span-2 sm:col-span-1"
          disabled={!dirty || !valid}
          loading={save.isPending}
          icon={<Save className="h-4 w-4" />}
          onClick={() => save.mutate()}
        >
          {tr.common.save}
        </Button>
      </div>
    </li>
  );
}

export function NutritionSettingsCard() {
  const q = useNutritionSettings();
  const order = { weight_loss: 0, maintenance: 1, weight_gain: 2 };
  return (
    <Card>
      <CardHeader title={tr.admin.nutritionSettings} subtitle={tr.admin.nutritionSettingsHint} icon={<Salad className="h-5 w-5" />} />
      {q.isLoading ? (
        <Skeleton className="m-5 h-40" />
      ) : q.error ? (
        <ErrorState message={errorMessage(q.error)} onRetry={() => q.refetch()} />
      ) : (
        <ul className="divide-y divide-line">
          {[...(q.data ?? [])]
            .sort((a, b) => order[a.goal] - order[b.goal])
            .map((r) => (
              <Row key={`${r.id}-${FIELDS.map((f) => r[f]).join('-')}`} row={r} />
            ))}
        </ul>
      )}
    </Card>
  );
}
