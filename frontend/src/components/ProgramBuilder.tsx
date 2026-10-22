import clsx from 'clsx';
import { ArrowDown, ArrowUp, Copy, Dumbbell, HeartPulse, Plus, Save, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  CARDIO_TYPES,
  MUSCLE_GROUPS,
  type Exercise,
  type LoadUnit,
  type Program,
  type ProgramDayInput,
  type ProgramInput,
  type ProgramItemInput,
} from '@/api/types';
import { useExercises } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { Button, Card, CardHeader, IconButton, Input, Select, Textarea } from './ui';

/* Local editing shapes carry a stable key for React lists. */
type ItemDraft = ProgramItemInput & { _key: number };
type DayDraft = Omit<ProgramDayInput, 'items'> & { _key: number; items: ItemDraft[] };
type Draft = Omit<ProgramInput, 'days'> & { days: DayDraft[] };

let keySeq = 1;
const nextKey = () => keySeq++;
const HR_ZONES: Record<number, [number, number]> = { 1: [50, 60], 2: [60, 70], 3: [70, 80], 4: [80, 90], 5: [90, 100] };

export function programToDraft(p?: Program | null): Draft {
  if (!p) return { title: '', goal: '', start_date: null, weeks: 4, days_per_week: 3, notes: '', days: [] };
  return {
    title: p.title,
    goal: p.goal ?? '',
    start_date: p.start_date,
    weeks: p.weeks,
    days_per_week: p.days_per_week,
    notes: p.notes ?? '',
    days: p.days.map((d) => ({
      _key: nextKey(),
      day_number: d.day_number,
      week_number: d.week_number,
      title: d.title,
      is_rest: d.is_rest,
      warmup: d.warmup ?? '',
      cooldown: d.cooldown ?? '',
      notes: d.notes ?? '',
      items: d.items.map(({ id: _id, exercise_name_ar: _a, exercise_name_en: _e, hr_target: _h, ...rest }) => ({ ...rest, _key: nextKey() })),
    })),
  };
}

const blank = (v: string | null | undefined) => (v == null || String(v).trim() === '' ? null : String(v).trim());
const numOrNull = (v: string) => (v.trim() === '' ? null : Number(v));

export function draftToInput(d: Draft): ProgramInput {
  return {
    title: d.title.trim(),
    goal: blank(d.goal),
    start_date: d.start_date || null,
    weeks: d.weeks,
    days_per_week: d.days_per_week,
    notes: blank(d.notes),
    days: d.days.map(({ _key, items, ...day }) => ({
      ...day,
      title: day.title.trim(),
      warmup: blank(day.warmup),
      cooldown: blank(day.cooldown),
      notes: blank(day.notes),
      items: day.is_rest
        ? []
        : items.map(({ _key: _k, ...it }) => ({
            ...it,
            custom_name: it.exercise_id ? null : blank(it.custom_name),
            reps: blank(it.reps),
            tempo: blank(it.tempo),
            notes: blank(it.notes),
            video_url: blank(it.video_url),
          })),
    })),
  };
}

function move<T>(arr: T[], i: number, dir: -1 | 1): T[] {
  const j = i + dir;
  if (j < 0 || j >= arr.length) return arr;
  const next = [...arr];
  [next[i], next[j]] = [next[j], next[i]];
  return next;
}

function NumField({ label, value, onChange, step = '1', className }: { label: string; value: number | null | undefined; onChange: (v: number | null) => void; step?: string; className?: string }) {
  return (
    <Input
      label={label}
      type="number"
      inputMode="decimal"
      dir="ltr"
      step={step}
      value={value ?? ''}
      onChange={(e) => onChange(numOrNull(e.target.value))}
      wrapperClassName={className}
      className="py-2"
    />
  );
}

function ExercisePicker({ item, library, onChange }: { item: ItemDraft; library: Exercise[]; onChange: (p: Partial<ItemDraft>) => void }) {
  const custom = !item.exercise_id;
  return (
    <div className="flex flex-col gap-2 sm:col-span-2">
      <Select
        label={tr.program.exercise}
        value={item.exercise_id ?? 'custom'}
        onChange={(e) => {
          const v = e.target.value;
          if (v === 'custom') onChange({ exercise_id: null });
          else {
            const ex = library.find((x) => x.id === Number(v));
            onChange({ exercise_id: Number(v), custom_name: null, muscle_group: ex?.muscle_group ?? item.muscle_group });
          }
        }}
      >
        <option value="custom">{tr.program.customExercise}</option>
        {MUSCLE_GROUPS.map((m) => {
          const list = library.filter((x) => x.muscle_group === m);
          if (!list.length) return null;
          return (
            <optgroup key={m} label={tr.muscles[m]}>
              {list.map((x) => (
                <option key={x.id} value={x.id}>
                  {loc(x.name_ar, x.name_en)}
                </option>
              ))}
            </optgroup>
          );
        })}
      </Select>
      {custom && (
        <div className="grid grid-cols-2 gap-2">
          <Input aria-label={tr.program.customName} placeholder={tr.program.customName} value={item.custom_name ?? ''} onChange={(e) => onChange({ custom_name: e.target.value })} className="py-2" />
          <Select aria-label={tr.program.muscle} value={item.muscle_group ?? ''} onChange={(e) => onChange({ muscle_group: e.target.value || null })} className="py-2">
            <option value="">{tr.program.muscle}</option>
            {MUSCLE_GROUPS.map((m) => (
              <option key={m} value={m}>
                {tr.muscles[m]}
              </option>
            ))}
          </Select>
        </div>
      )}
    </div>
  );
}

function ItemEditor({
  item,
  library,
  maxHr,
  onChange,
  onMove,
  onRemove,
  first,
  last,
}: {
  item: ItemDraft;
  library: Exercise[];
  maxHr: number | null;
  onChange: (p: Partial<ItemDraft>) => void;
  onMove: (dir: -1 | 1) => void;
  onRemove: () => void;
  first: boolean;
  last: boolean;
}) {
  const isCardio = item.kind === 'cardio';
  const zone = item.hr_zone ? HR_ZONES[item.hr_zone] : null;
  return (
    <li className={clsx('rounded-xl border p-3', isCardio ? 'border-bad/30 bg-bad/5' : 'border-line bg-surface')}>
      <div className="mb-2 flex items-center gap-2">
        {isCardio ? <HeartPulse className="h-4 w-4 text-bad" /> : <Dumbbell className="h-4 w-4 text-primary" />}
        <span className="text-xs font-bold text-muted">{isCardio ? tr.program.cardio : tr.program.resistance}</span>
        <div className="ms-auto flex">
          <IconButton label={tr.program.moveUp} onClick={() => onMove(-1)} disabled={first} className="h-8 w-8 disabled:opacity-30">
            <ArrowUp className="h-4 w-4" />
          </IconButton>
          <IconButton label={tr.program.moveDown} onClick={() => onMove(1)} disabled={last} className="h-8 w-8 disabled:opacity-30">
            <ArrowDown className="h-4 w-4" />
          </IconButton>
          <IconButton label={tr.program.remove} onClick={onRemove} className="h-8 w-8 hover:text-bad">
            <Trash2 className="h-4 w-4" />
          </IconButton>
        </div>
      </div>
      {isCardio ? (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Select label={tr.program.type} value={item.cardio_type ?? ''} onChange={(e) => onChange({ cardio_type: e.target.value })} wrapperClassName="col-span-2" className="py-2">
            {CARDIO_TYPES.map((c) => (
              <option key={c} value={c}>
                {tr.cardioTypes[c]}
              </option>
            ))}
          </Select>
          <NumField label={tr.program.duration} value={item.duration_min} onChange={(v) => onChange({ duration_min: v })} step="any" />
          <Select
            label={tr.program.zone}
            value={item.hr_zone ?? ''}
            onChange={(e) => onChange({ hr_zone: e.target.value ? Number(e.target.value) : null })}
            hint={zone && maxHr ? tr.program.targetHr(Math.round((maxHr * zone[0]) / 100), Math.round((maxHr * zone[1]) / 100)) : undefined}
            className="py-2"
          >
            <option value="">—</option>
            {[1, 2, 3, 4, 5].map((z) => (
              <option key={z} value={z}>
                {tr.program.zoneN(z)} ({HR_ZONES[z][0]}–{HR_ZONES[z][1]}%)
              </option>
            ))}
          </Select>
          <NumField label={tr.program.speed} value={item.speed} onChange={(v) => onChange({ speed: v })} step="any" />
          <NumField label={tr.program.incline} value={item.incline} onChange={(v) => onChange({ incline: v })} step="any" />
          <NumField label={tr.program.work} value={item.work_seconds} onChange={(v) => onChange({ work_seconds: v })} />
          <NumField label={tr.program.intervalRest} value={item.interval_rest_seconds} onChange={(v) => onChange({ interval_rest_seconds: v })} />
          <NumField label={tr.program.rounds} value={item.rounds} onChange={(v) => onChange({ rounds: v })} />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <ExercisePicker item={item} library={library} onChange={onChange} />
          <NumField label={tr.program.sets} value={item.sets} onChange={(v) => onChange({ sets: v })} />
          <Input label={tr.program.reps} dir="ltr" placeholder="8-12" value={item.reps ?? ''} onChange={(e) => onChange({ reps: e.target.value })} className="py-2" />
          <div className="col-span-2 grid grid-cols-[1fr_auto] gap-2 sm:col-span-1">
            <NumField label={tr.program.load} value={item.load_value} onChange={(v) => onChange({ load_value: v })} step="any" />
            <Select aria-label={tr.program.load} label={' '} value={item.load_unit ?? 'kg'} onChange={(e) => onChange({ load_unit: e.target.value as LoadUnit })} className="py-2">
              {(['kg', 'pct_1rm', 'rpe'] as LoadUnit[]).map((u) => (
                <option key={u} value={u}>
                  {tr.loadUnits[u]}
                </option>
              ))}
            </Select>
          </div>
          <NumField label={tr.program.rest} value={item.rest_seconds} onChange={(v) => onChange({ rest_seconds: v })} />
          <Input label={tr.program.tempo} dir="ltr" placeholder="3-1-1-0" value={item.tempo ?? ''} onChange={(e) => onChange({ tempo: e.target.value })} className="py-2" />
        </div>
      )}
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <Input aria-label={tr.common.notes} placeholder={tr.common.notes} value={item.notes ?? ''} onChange={(e) => onChange({ notes: e.target.value })} className="py-2" />
        <Input aria-label={tr.program.video} placeholder={`${tr.program.video} (https://…)`} dir="ltr" value={item.video_url ?? ''} onChange={(e) => onChange({ video_url: e.target.value })} className="py-2" />
      </div>
    </li>
  );
}

function DayEditor({
  day,
  weeks,
  library,
  maxHr,
  onChange,
  onCopy,
  onRemove,
  onMove,
  first,
  last,
}: {
  day: DayDraft;
  weeks: number;
  library: Exercise[];
  maxHr: number | null;
  onChange: (p: Partial<DayDraft>) => void;
  onCopy: () => void;
  onRemove: () => void;
  onMove: (dir: -1 | 1) => void;
  first: boolean;
  last: boolean;
}) {
  const setItem = (i: number, p: Partial<ItemDraft>) => onChange({ items: day.items.map((it, j) => (j === i ? { ...it, ...p } : it)) });
  const addItem = (kind: 'resistance' | 'cardio') =>
    onChange({
      items: [
        ...day.items,
        kind === 'resistance'
          ? { _key: nextKey(), kind, exercise_id: null, custom_name: '', sets: 3, reps: '10', load_unit: 'kg', rest_seconds: 60 }
          : { _key: nextKey(), kind, cardio_type: 'treadmill', duration_min: 20, hr_zone: 2 },
      ],
    });
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-end gap-2 border-b border-line bg-surface-2/50 p-3">
        <Select label={tr.program.dayNumber} value={day.day_number} onChange={(e) => onChange({ day_number: Number(e.target.value) })} wrapperClassName="w-24" className="py-2">
          {[1, 2, 3, 4, 5, 6, 7].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </Select>
        <Select
          label={tr.program.week}
          value={day.week_number ?? ''}
          onChange={(e) => onChange({ week_number: e.target.value ? Number(e.target.value) : null })}
          wrapperClassName="w-36"
          className="py-2"
        >
          <option value="">{tr.program.everyWeek}</option>
          {Array.from({ length: weeks }, (_, i) => i + 1).map((w) => (
            <option key={w} value={w}>
              {tr.program.weekN(w)}
            </option>
          ))}
        </Select>
        <Input
          label={tr.program.dayTitle}
          placeholder={tr.program.dayTitlePlaceholder}
          value={day.title}
          onChange={(e) => onChange({ title: e.target.value })}
          wrapperClassName="min-w-[12rem] flex-1"
          className="py-2"
        />
        <label className="flex h-10 items-center gap-2 text-sm font-medium">
          <input type="checkbox" checked={day.is_rest} onChange={(e) => onChange({ is_rest: e.target.checked })} className="h-4 w-4 accent-[rgb(var(--c-primary))]" />
          {tr.program.restDay}
        </label>
        <div className="flex">
          <IconButton label={tr.program.moveUp} onClick={() => onMove(-1)} disabled={first} className="disabled:opacity-30">
            <ArrowUp className="h-4 w-4" />
          </IconButton>
          <IconButton label={tr.program.moveDown} onClick={() => onMove(1)} disabled={last} className="disabled:opacity-30">
            <ArrowDown className="h-4 w-4" />
          </IconButton>
          <IconButton label={tr.program.copyDay} onClick={onCopy}>
            <Copy className="h-4 w-4" />
          </IconButton>
          <IconButton label={tr.program.deleteDay} onClick={onRemove} className="hover:text-bad">
            <Trash2 className="h-4 w-4" />
          </IconButton>
        </div>
      </div>
      {!day.is_rest && (
        <div className="flex flex-col gap-3 p-3">
          <div className="grid gap-2 sm:grid-cols-2">
            <Input aria-label={tr.program.warmup} placeholder={tr.program.warmup} value={day.warmup ?? ''} onChange={(e) => onChange({ warmup: e.target.value })} className="py-2" />
            <Input aria-label={tr.program.cooldown} placeholder={tr.program.cooldown} value={day.cooldown ?? ''} onChange={(e) => onChange({ cooldown: e.target.value })} className="py-2" />
          </div>
          <ul className="flex flex-col gap-2">
            {day.items.map((it, i) => (
              <ItemEditor
                key={it._key}
                item={it}
                library={library}
                maxHr={maxHr}
                onChange={(p) => setItem(i, p)}
                onMove={(dir) => onChange({ items: move(day.items, i, dir) })}
                onRemove={() => onChange({ items: day.items.filter((_, j) => j !== i) })}
                first={i === 0}
                last={i === day.items.length - 1}
              />
            ))}
          </ul>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" icon={<Plus className="h-4 w-4" />} onClick={() => addItem('resistance')}>
              {tr.program.addResistance}
            </Button>
            <Button size="sm" variant="outline" icon={<Plus className="h-4 w-4" />} onClick={() => addItem('cardio')}>
              {tr.program.addCardio}
            </Button>
          </div>
        </div>
      )}
      <div className="px-3 pb-3">
        <Textarea aria-label={tr.common.notes} placeholder={tr.common.notes} rows={1} value={day.notes ?? ''} onChange={(e) => onChange({ notes: e.target.value })} />
      </div>
    </Card>
  );
}

function freeDayNumber(days: DayDraft[], week: number | null): number {
  const used = new Set(days.filter((d) => d.week_number === week).map((d) => d.day_number));
  for (let n = 1; n <= 7; n++) if (!used.has(n)) return n;
  return 7;
}

/** Edits a program tree. The parent decides what "save" does (create or update). */
export function ProgramBuilder({
  initial,
  maxHr,
  saving,
  onSave,
  actions,
  hideStartDate,
}: {
  initial?: Program | null;
  maxHr: number | null;
  saving: boolean;
  onSave: (input: ProgramInput) => void;
  actions?: React.ReactNode;
  hideStartDate?: boolean;
}) {
  const library = useExercises().data ?? [];
  const [draft, setDraft] = useState<Draft>(() => programToDraft(initial));
  const [dirty, setDirty] = useState(false);
  const update = (p: Partial<Draft>) => {
    setDraft((d) => ({ ...d, ...p }));
    setDirty(true);
  };
  const setDay = (i: number, p: Partial<DayDraft>) => update({ days: draft.days.map((d, j) => (j === i ? { ...d, ...p } : d)) });
  const valid = useMemo(() => draft.title.trim().length > 0 && draft.days.every((d) => d.title.trim()), [draft]);

  const addDay = () =>
    update({
      days: [
        ...draft.days,
        { _key: nextKey(), day_number: freeDayNumber(draft.days, null), week_number: null, title: tr.program.dayN(draft.days.length + 1), is_rest: false, items: [] },
      ],
    });
  const copyDay = (i: number) => {
    const src = draft.days[i];
    const copy: DayDraft = { ...src, _key: nextKey(), day_number: freeDayNumber(draft.days, src.week_number), items: src.items.map((it) => ({ ...it, _key: nextKey() })) };
    update({ days: [...draft.days.slice(0, i + 1), copy, ...draft.days.slice(i + 1)] });
  };

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        onSave(draftToInput(draft));
        setDirty(false);
      }}
    >
      <Card>
        <CardHeader title={tr.program.details} actions={dirty ? <span className="text-xs text-warn">{tr.program.unsaved}</span> : undefined} />
        <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Input label={tr.program.name} value={draft.title} onChange={(e) => update({ title: e.target.value })} wrapperClassName="sm:col-span-2" required />
          <Input label={tr.program.goal} value={draft.goal ?? ''} onChange={(e) => update({ goal: e.target.value })} wrapperClassName="sm:col-span-2" />
          {!hideStartDate && <Input label={tr.program.startDate} type="date" value={draft.start_date ?? ''} onChange={(e) => update({ start_date: e.target.value || null })} />}
          <NumField label={tr.program.weeks} value={draft.weeks} onChange={(v) => update({ weeks: Math.max(1, Math.min(52, v ?? 1)) })} />
          <NumField label={tr.program.daysPerWeek} value={draft.days_per_week} onChange={(v) => update({ days_per_week: Math.max(1, Math.min(7, v ?? 1)) })} />
          <Textarea label={tr.program.notes} rows={2} value={draft.notes ?? ''} onChange={(e) => update({ notes: e.target.value })} wrapperClassName="sm:col-span-2 lg:col-span-4" />
        </div>
      </Card>

      <div className="flex flex-col gap-3">
        {draft.days.map((d, i) => (
          <DayEditor
            key={d._key}
            day={d}
            weeks={draft.weeks}
            library={library}
            maxHr={maxHr}
            onChange={(p) => setDay(i, p)}
            onCopy={() => copyDay(i)}
            onRemove={() => update({ days: draft.days.filter((_, j) => j !== i) })}
            onMove={(dir) => update({ days: move(draft.days, i, dir) })}
            first={i === 0}
            last={i === draft.days.length - 1}
          />
        ))}
        <Button variant="outline" icon={<Plus className="h-4 w-4" />} onClick={addDay} className="self-start">
          {tr.program.addDay}
        </Button>
      </div>

      <div className="sticky bottom-[calc(4.75rem+env(safe-area-inset-bottom))] z-10 flex flex-wrap gap-2 rounded-2xl border border-line bg-surface/95 p-3 shadow-lg backdrop-blur md:bottom-4">
        <Button type="submit" loading={saving} disabled={!valid} icon={<Save className="h-4 w-4" />}>
          {tr.program.save}
        </Button>
        {actions}
      </div>
    </form>
  );
}
