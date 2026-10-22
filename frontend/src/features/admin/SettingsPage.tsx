import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';
import { Gauge, Plus, Save, Sliders } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { adminApi } from '@/api/endpoints';
import { CATEGORIES, type ActivityFactor, type Category, type ChoiceOption, type Definition, type Direction, type ValueType } from '@/api/types';
import { Badge, Button, Card, CardHeader, ErrorState, Input, Modal, PageHeader, Select, Skeleton, Textarea } from '@/components/ui';
import { qk } from '@/hooks/queries';
import { tr } from '@/i18n';

const numOrNull = (s: string) => (s.trim() === '' ? null : Number(s));

function useInvalidateDefs() {
  const qc = useQueryClient();
  return () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: qk.adminDefinitions }),
      qc.invalidateQueries({ queryKey: qk.definitions }),
      qc.invalidateQueries({ queryKey: ['client'] }),
    ]);
}

function DefinitionRow({ def }: { def: Definition }) {
  const invalidate = useInvalidateDefs();
  const [name, setName] = useState(def.name_ar);
  const [nameEn, setNameEn] = useState(def.name_en ?? '');
  const [unit, setUnit] = useState(def.unit ?? '');
  const [unitEn, setUnitEn] = useState(def.unit_en ?? '');
  const [min, setMin] = useState(def.min_value?.toString() ?? '');
  const [max, setMax] = useState(def.max_value?.toString() ?? '');
  const [direction, setDirection] = useState<Direction>(def.better_direction);

  const dirty =
    name !== def.name_ar ||
    nameEn !== (def.name_en ?? '') ||
    unit !== (def.unit ?? '') ||
    unitEn !== (def.unit_en ?? '') ||
    min !== (def.min_value?.toString() ?? '') ||
    max !== (def.max_value?.toString() ?? '') ||
    direction !== def.better_direction;

  const save = useMutation({
    mutationFn: (body: Partial<Definition>) => adminApi.updateDefinition(def.id, body),
    onSuccess: async () => {
      toast.success(tr.admin.definitionSaved);
      await invalidate();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const numeric = def.value_type === 'number';
  return (
    <li className={clsx('grid gap-3 px-4 py-3 sm:px-5 sm:grid-cols-2 lg:grid-cols-4 lg:items-end', !def.is_active && 'opacity-60')}>
      <Input
        label={
          <span className="flex items-center gap-2">
            {tr.admin.nameAr}
            <code className="text-[11px] font-normal text-muted" dir="ltr">
              {def.key}
            </code>
            <Badge>{tr.valueTypes[def.value_type]}</Badge>
          </span>
        }
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <Input label={tr.admin.nameEn} dir="ltr" value={nameEn} onChange={(e) => setNameEn(e.target.value)} />
      <Input label={tr.admin.unit} value={unit} onChange={(e) => setUnit(e.target.value)} />
      <Input label={tr.admin.unitEn} dir="ltr" value={unitEn} onChange={(e) => setUnitEn(e.target.value)} />
      <Input label={tr.admin.min} type="number" dir="ltr" value={min} disabled={!numeric} onChange={(e) => setMin(e.target.value)} />
      <Input label={tr.admin.max} type="number" dir="ltr" value={max} disabled={!numeric} onChange={(e) => setMax(e.target.value)} />
      <Select label={tr.admin.direction} value={direction} onChange={(e) => setDirection(e.target.value as Direction)}>
        {(['up', 'down', 'none'] as Direction[]).map((d) => (
          <option key={d} value={d}>
            {tr.directions[d]}
          </option>
        ))}
      </Select>
      <div className="flex gap-2">
        <Button
          size="md"
          disabled={!dirty || !name.trim()}
          loading={save.isPending}
          icon={<Save className="h-4 w-4" />}
          onClick={() =>
            save.mutate({
              name_ar: name.trim(),
              name_en: nameEn.trim() || null,
              unit: unit.trim() || null,
              unit_en: unitEn.trim() || null,
              better_direction: direction,
              ...(numeric ? { min_value: numOrNull(min), max_value: numOrNull(max) } : {}),
            })
          }
        >
          {tr.common.save}
        </Button>
        <Button variant={def.is_active ? 'outline' : 'secondary'} onClick={() => save.mutate({ is_active: !def.is_active })}>
          {def.is_active ? tr.admin.deactivate : tr.admin.activate}
        </Button>
      </div>
    </li>
  );
}

function parseChoices(text: string): ChoiceOption[] | null {
  const out: ChoiceOption[] = [];
  for (const line of text.split('\n').map((l) => l.trim()).filter(Boolean)) {
    const [v, ...rest] = line.split('=');
    const value = Number(v);
    const [label, labelEn] = rest.join('=').split('|').map((x) => x.trim());
    if (Number.isNaN(value) || !label) return null;
    out.push({ value, label, label_en: labelEn || null });
  }
  return out.length ? out : null;
}

function NewDefinitionModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const invalidate = useInvalidateDefs();
  const [form, setForm] = useState({
    key: '',
    name_ar: '',
    name_en: '',
    unit_en: '',
    category: 'body' as Category,
    unit: '',
    value_type: 'number' as ValueType,
    better_direction: 'none' as Direction,
    min: '',
    max: '',
    choices: '',
  });
  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) => setForm((f) => ({ ...f, [k]: v }));
  const keyValid = /^[a-z][a-z0-9_]{1,49}$/.test(form.key);

  const create = useMutation({
    mutationFn: () => {
      const choices = form.value_type === 'choice' ? parseChoices(form.choices) : null;
      if (form.value_type === 'choice' && !choices) throw new Error(tr.admin.choicesHint);
      return adminApi.createDefinition({
        key: form.key,
        name_ar: form.name_ar.trim(),
        name_en: form.name_en.trim() || null,
        unit_en: form.unit_en.trim() || null,
        category: form.category,
        unit: form.unit.trim() || null,
        value_type: form.value_type,
        better_direction: form.better_direction,
        min_value: numOrNull(form.min),
        max_value: numOrNull(form.max),
        choices,
      });
    },
    onSuccess: async () => {
      toast.success(tr.admin.definitionSaved);
      await invalidate();
      onClose();
    },
    onError: (e) => toast.error(e instanceof Error && !('isAxiosError' in e) ? e.message : errorMessage(e)),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={tr.admin.newDefinition}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {tr.common.cancel}
          </Button>
          <Button onClick={() => create.mutate()} loading={create.isPending} disabled={!keyValid || !form.name_ar.trim()}>
            {tr.common.create}
          </Button>
        </>
      }
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label={tr.admin.key}
          dir="ltr"
          value={form.key}
          onChange={(e) => set('key', e.target.value.toLowerCase())}
          hint={tr.admin.keyHint}
          error={form.key && !keyValid ? tr.admin.keyHint : undefined}
        />
        <Input label={tr.admin.nameAr} value={form.name_ar} onChange={(e) => set('name_ar', e.target.value)} />
        <Input label={tr.admin.nameEn} dir="ltr" value={form.name_en} onChange={(e) => set('name_en', e.target.value)} />
        <Select label={tr.admin.category} value={form.category} onChange={(e) => set('category', e.target.value as Category)}>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {tr.categories[c]}
            </option>
          ))}
        </Select>
        <Select label={tr.admin.valueType} value={form.value_type} onChange={(e) => set('value_type', e.target.value as ValueType)}>
          {(['number', 'choice', 'text'] as ValueType[]).map((t) => (
            <option key={t} value={t}>
              {tr.valueTypes[t]}
            </option>
          ))}
        </Select>
        <Input label={tr.admin.unit} value={form.unit} onChange={(e) => set('unit', e.target.value)} />
        <Input label={tr.admin.unitEn} dir="ltr" value={form.unit_en} onChange={(e) => set('unit_en', e.target.value)} />
        <Select label={tr.admin.direction} value={form.better_direction} onChange={(e) => set('better_direction', e.target.value as Direction)}>
          {(['up', 'down', 'none'] as Direction[]).map((d) => (
            <option key={d} value={d}>
              {tr.directions[d]}
            </option>
          ))}
        </Select>
        {form.value_type !== 'text' && (
          <>
            <Input label={tr.admin.min} type="number" dir="ltr" value={form.min} onChange={(e) => set('min', e.target.value)} />
            <Input label={tr.admin.max} type="number" dir="ltr" value={form.max} onChange={(e) => set('max', e.target.value)} />
          </>
        )}
        {form.value_type === 'choice' && (
          <Textarea
            label={tr.admin.choices}
            hint={`${tr.admin.choicesHint} · ${tr.admin.choicesEnHint}`}
            rows={4}
            wrapperClassName="sm:col-span-2"
            value={form.choices}
            onChange={(e) => set('choices', e.target.value)}
          />
        )}
      </div>
    </Modal>
  );
}

function FactorRow({ f }: { f: ActivityFactor }) {
  const qc = useQueryClient();
  const [name, setName] = useState(f.name_ar);
  const [nameEn, setNameEn] = useState(f.name_en ?? '');
  const [desc, setDesc] = useState(f.description_ar ?? '');
  const [descEn, setDescEn] = useState(f.description_en ?? '');
  const [factor, setFactor] = useState(String(f.factor));
  const dirty =
    name !== f.name_ar ||
    nameEn !== (f.name_en ?? '') ||
    desc !== (f.description_ar ?? '') ||
    descEn !== (f.description_en ?? '') ||
    factor !== String(f.factor);
  const n = Number(factor);
  const valid = !Number.isNaN(n) && n >= 1 && n <= 2.5;

  const save = useMutation({
    mutationFn: () => adminApi.updateActivityFactor(f.id, {
        name_ar: name.trim(),
        name_en: nameEn.trim() || null,
        description_ar: desc.trim(),
        description_en: descEn.trim() || null,
        factor: n,
      }),
    onSuccess: async () => {
      toast.success(tr.admin.factorSaved);
      await Promise.all([
        qc.invalidateQueries({ queryKey: qk.adminFactors }),
        qc.invalidateQueries({ queryKey: qk.activityFactors }),
        qc.invalidateQueries({ queryKey: ['client'] }),
      ]);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <li className="grid gap-3 px-4 py-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1.4fr_1.4fr_7rem_auto] lg:items-end sm:px-5">
      <Input label={tr.admin.nameAr} value={name} onChange={(e) => setName(e.target.value)} />
      <Input label={tr.admin.nameEn} dir="ltr" value={nameEn} onChange={(e) => setNameEn(e.target.value)} />
      <Input label={tr.admin.description} value={desc} onChange={(e) => setDesc(e.target.value)} />
      <Input label={tr.admin.descriptionEn} dir="ltr" value={descEn} onChange={(e) => setDescEn(e.target.value)} />
      <Input
        label={tr.admin.factor}
        type="number"
        step="0.05"
        dir="ltr"
        value={factor}
        onChange={(e) => setFactor(e.target.value)}
        error={valid ? undefined : '1.0 – 2.5'}
      />
      <Button disabled={!dirty || !valid} loading={save.isPending} icon={<Save className="h-4 w-4" />} onClick={() => save.mutate()}>
        {tr.common.save}
      </Button>
    </li>
  );
}

export function SettingsPage() {
  const defs = useQuery({ queryKey: qk.adminDefinitions, queryFn: adminApi.definitions });
  const factors = useQuery({ queryKey: qk.adminFactors, queryFn: adminApi.activityFactors });
  const [showNew, setShowNew] = useState(false);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={tr.admin.settingsTitle}
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => setShowNew(true)}>
            {tr.admin.newDefinition}
          </Button>
        }
      />

      <Card>
        <CardHeader title={tr.admin.activityFactors} subtitle={tr.admin.activityHint} icon={<Gauge className="h-5 w-5" />} />
        {factors.isLoading ? (
          <Skeleton className="m-5 h-40" />
        ) : factors.error ? (
          <ErrorState message={errorMessage(factors.error)} onRetry={() => factors.refetch()} />
        ) : (
          <ul className="divide-y divide-line">
            {factors.data?.map((f) => (
              <FactorRow key={`${f.id}-${f.factor}-${f.name_ar}-${f.name_en}-${f.description_ar}-${f.description_en}`} f={f} />
            ))}
          </ul>
        )}
      </Card>

      {defs.isLoading ? (
        <Skeleton className="h-96" />
      ) : defs.error ? (
        <ErrorState message={errorMessage(defs.error)} onRetry={() => defs.refetch()} />
      ) : (
        CATEGORIES.map((cat) => (
          <Card key={cat}>
            <CardHeader title={tr.categories[cat]} subtitle={tr.admin.definitions} icon={<Sliders className="h-5 w-5" />} />
            <ul className="divide-y divide-line">
              {defs.data
                ?.filter((d) => d.category === cat)
                .map((d) => (
                  <DefinitionRow key={`${d.id}-${d.is_active}-${d.name_ar}-${d.name_en}-${d.unit}-${d.unit_en}-${d.min_value}-${d.max_value}-${d.better_direction}`} def={d} />
                ))}
            </ul>
          </Card>
        ))
      )}

      {showNew && <NewDefinitionModal open onClose={() => setShowNew(false)} />}
    </div>
  );
}
