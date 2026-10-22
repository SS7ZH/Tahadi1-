import clsx from 'clsx';
import { CalendarDays, Dumbbell, ExternalLink, FileDown, HeartPulse, MessageCircleQuestion, Moon, Timer } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import type { Program, ProgramDay, ProgramItem } from '@/api/types';
import { loc, tr } from '@/i18n';
import { downloadPdf } from '@/lib/download';
import { fmtDate, fmtNumber, fmtShortDate, parseDate } from '@/lib/format';
import { Badge, Button, Card, Select } from './ui';

export function itemName(it: ProgramItem): string {
  if (it.kind === 'cardio') return tr.cardioTypes[it.cardio_type ?? ''] ?? it.cardio_type ?? '';
  return loc(it.exercise_name_ar, it.exercise_name_en) || it.custom_name || '—';
}

export function loadText(it: Pick<ProgramItem, 'load_value' | 'load_unit'>): string | null {
  if (it.load_value == null) return null;
  if (it.load_unit === 'pct_1rm') return `${fmtNumber(it.load_value)}% 1RM`;
  if (it.load_unit === 'rpe') return `RPE ${fmtNumber(it.load_value)}`;
  return `${fmtNumber(it.load_value)} ${tr.common.kg}`;
}

/** Day shown for a week slot: a week-specific day wins over a repeating one. */
export function dayFor(program: Program, week: number, dayNumber: number): ProgramDay | undefined {
  return (
    program.days.find((d) => d.week_number === week && d.day_number === dayNumber) ??
    program.days.find((d) => d.week_number == null && d.day_number === dayNumber)
  );
}

function slotDate(program: Program, week: number, dayNumber: number): string | null {
  if (!program.start_date) return null;
  const d = parseDate(program.start_date);
  d.setDate(d.getDate() + (week - 1) * 7 + dayNumber - 1);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function Chip({ children }: { children: React.ReactNode }) {
  return <span className="num inline-flex items-center rounded-lg bg-surface-2 px-2 py-0.5 text-xs font-semibold">{children}</span>;
}

function ItemRow({ it }: { it: ProgramItem }) {
  const load = loadText(it);
  return (
    <li className="flex flex-col gap-1.5 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        {it.kind === 'cardio' ? <HeartPulse className="h-4 w-4 text-bad" /> : <Dumbbell className="h-4 w-4 text-primary" />}
        <span className="font-semibold">{itemName(it)}</span>
        {it.muscle_group && it.kind === 'resistance' && <Badge>{tr.muscles[it.muscle_group] ?? it.muscle_group}</Badge>}
        {it.video_url && (
          <a href={it.video_url} target="_blank" rel="noopener noreferrer" className="ms-auto inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline">
            <ExternalLink className="h-3.5 w-3.5" />
            {tr.program.watch}
          </a>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5 ps-6">
        {it.kind === 'resistance' ? (
          <>
            {(it.sets || it.reps) && <Chip>{tr.program.setsReps(it.sets ?? '—', it.reps ?? '—')}</Chip>}
            {load && <Chip>{load}</Chip>}
            {it.rest_seconds != null && (
              <Chip>
                <Timer className="me-1 h-3 w-3" />
                {it.rest_seconds}
                {tr.program.secUnit}
              </Chip>
            )}
            {it.tempo && <Chip>{tr.program.tempo}: {it.tempo}</Chip>}
          </>
        ) : (
          <>
            {it.duration_min != null && <Chip>{fmtNumber(it.duration_min)} {tr.program.minUnit}</Chip>}
            {it.hr_zone != null && (
              <Chip>
                {tr.program.zoneN(it.hr_zone)}
                {it.hr_target && <span className="ms-1 font-normal text-muted">({tr.program.targetHr(it.hr_target.min_bpm, it.hr_target.max_bpm)})</span>}
              </Chip>
            )}
            {it.speed != null && <Chip>{fmtNumber(it.speed)} {tr.program.kmh}</Chip>}
            {it.incline != null && <Chip>{fmtNumber(it.incline)}%</Chip>}
            {it.work_seconds != null && it.rounds != null && (
              <Chip>
                {it.rounds} × ({it.work_seconds}
                {tr.program.secUnit} / {it.interval_rest_seconds ?? 0}
                {tr.program.secUnit})
              </Chip>
            )}
          </>
        )}
      </div>
      {it.notes && <p className="ps-6 text-xs text-ink/70">{it.notes}</p>}
    </li>
  );
}

export function DayCard({
  day,
  date,
  highlight,
  askHref,
}: {
  day: ProgramDay | undefined;
  date?: string | null;
  highlight?: boolean;
  askHref?: (dayId: number) => string;
}) {
  const rest = !day || day.is_rest;
  const resistance = day?.items.filter((i) => i.kind === 'resistance') ?? [];
  const cardio = day?.items.filter((i) => i.kind === 'cardio') ?? [];
  return (
    <Card className={clsx('overflow-hidden', highlight && 'border-primary ring-2 ring-primary/30')}>
      <div className={clsx('flex flex-wrap items-center gap-2 px-4 py-3', highlight ? 'bg-primary/10' : 'border-b border-line')}>
        {rest ? <Moon className="h-4 w-4 text-muted" /> : <CalendarDays className="h-4 w-4 text-primary" />}
        <span className="font-bold">{day?.title ?? tr.program.restDay}</span>
        {date && <span className="text-xs text-muted">{fmtDate(date)}</span>}
        {highlight && <Badge tone="primary">{tr.program.today}</Badge>}
        {day && !rest && askHref && (
          <Link to={askHref(day.id)} className="ms-auto inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline">
            <MessageCircleQuestion className="h-3.5 w-3.5" />
            {tr.program.askAboutDay}
          </Link>
        )}
      </div>
      {!rest && day && (
        <div className="flex flex-col gap-3 px-4 pb-3 pt-2">
          {day.warmup && (
            <p className="text-sm">
              <b>{tr.program.warmup}:</b> {day.warmup}
            </p>
          )}
          {resistance.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-muted">{tr.program.resistance}</h4>
              <ul className="divide-y divide-line">
                {resistance.map((it) => (
                  <ItemRow key={it.id} it={it} />
                ))}
              </ul>
            </div>
          )}
          {cardio.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-muted">{tr.program.cardio}</h4>
              <ul className="divide-y divide-line">
                {cardio.map((it) => (
                  <ItemRow key={it.id} it={it} />
                ))}
              </ul>
            </div>
          )}
          {!day.items.length && <p className="text-sm text-muted">{tr.program.noItems}</p>}
          {day.cooldown && (
            <p className="text-sm">
              <b>{tr.program.cooldown}:</b> {day.cooldown}
            </p>
          )}
          {day.notes && <p className="rounded-xl bg-surface-2 px-3 py-2 text-sm">{day.notes}</p>}
        </div>
      )}
    </Card>
  );
}

/** Read-only program: today's workout highlighted, then the selected week. */
export function ProgramView({ program, askHref }: { program: Program; askHref?: (dayId: number) => string }) {
  const today = program.today;
  const currentWeek = today?.week ?? 1;
  const [week, setWeek] = useState(currentWeek);
  const [exporting, setExporting] = useState(false);
  const todayDay = today?.day_id ? program.days.find((d) => d.id === today.day_id) : undefined;

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadPdf(`/pdf/program/${program.id}`);
      toast.success(tr.pdf.exported);
    } catch (err) {
      toast.error(errorMessage(err) || tr.pdf.exportFailed);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col gap-2 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold">{program.title}</h2>
            <Badge tone={program.status === 'active' ? 'good' : program.status === 'draft' ? 'warn' : 'neutral'}>
              {tr.programStatus[program.status]}
            </Badge>
          </div>
          <Button
            variant="outline"
            size="sm"
            icon={<FileDown className="h-4 w-4" />}
            loading={exporting}
            onClick={handleExport}
          >
            {tr.pdf.exportPdf}
          </Button>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
          {program.goal && (
            <span>
              {tr.program.goal}: <b className="text-ink">{program.goal}</b>
            </span>
          )}
          <span>
            {tr.program.startDate}: <b className="text-ink">{program.start_date ? fmtDate(program.start_date) : '—'}</b>
          </span>
          <span>
            {tr.program.weeks}: <b className="num text-ink">{program.weeks}</b>
          </span>
          <span>
            {tr.program.daysPerWeek}: <b className="num text-ink">{program.days_per_week}</b>
          </span>
          {program.max_hr && <span>{tr.program.maxHr(program.max_hr)}</span>}
        </div>
        {program.notes && <p className="whitespace-pre-line text-sm">{program.notes}</p>}
      </Card>

      {today && (
        <section>
          <h3 className="mb-2 flex items-center gap-2 font-bold">
            {tr.program.today}
            {today.state === 'running' && today.week && (
              <span className="text-xs font-normal text-muted">
                {tr.program.weekOf(today.week, program.weeks)} · {fmtShortDate(slotDate(program, today.week, today.day_number ?? 1))}
              </span>
            )}
          </h3>
          {today.state === 'finished' ? (
            <Card className="p-4 text-sm text-muted">{tr.program.finished}</Card>
          ) : today.state === 'no_start_date' ? (
            <Card className="p-4 text-sm text-muted">{tr.program.noStart}</Card>
          ) : (
            <>
              {today.state === 'not_started' && <p className="mb-2 text-sm text-muted">{tr.program.notStarted(today.starts_in_days ?? 0)}</p>}
              {todayDay && !todayDay.is_rest ? (
                <DayCard day={todayDay} highlight askHref={askHref} />
              ) : (
                <Card className="border-primary p-4 text-sm font-semibold ring-2 ring-primary/30">{tr.program.todayRest}</Card>
              )}
            </>
          )}
        </section>
      )}

      <section>
        <div className="mb-2 flex flex-wrap items-end justify-between gap-2">
          <h3 className="font-bold">{week === currentWeek ? tr.program.thisWeek : tr.program.weekN(week)}</h3>
          {program.weeks > 1 && (
            <Select aria-label={tr.program.week} value={week} onChange={(e) => setWeek(Number(e.target.value))} wrapperClassName="w-40">
              {Array.from({ length: program.weeks }, (_, i) => i + 1).map((w) => (
                <option key={w} value={w}>
                  {tr.program.weekN(w)}
                </option>
              ))}
            </Select>
          )}
        </div>
        <div className="flex flex-col gap-3">
          {Array.from({ length: 7 }, (_, i) => i + 1).map((dn) => {
            const day = dayFor(program, week, dn);
            const isToday = today?.state === 'running' && today.week === week && today.day_number === dn;
            if (!day || day.is_rest) {
              const date = slotDate(program, week, dn);
              return (
                <div key={dn} className={clsx('flex items-center gap-2 rounded-xl border border-dashed border-line px-4 py-2.5 text-sm text-muted', isToday && 'border-primary text-ink')}>
                  <Moon className="h-4 w-4" />
                  {day?.title ?? tr.program.restDay}
                  <span className="text-xs">· {tr.program.dayN(dn)}</span>
                  {date && <span className="ms-auto text-xs">{fmtShortDate(date)}</span>}
                </div>
              );
            }
            return <DayCard key={dn} day={day} date={slotDate(program, week, dn)} highlight={isToday} askHref={askHref} />;
          })}
        </div>
      </section>
    </div>
  );
}
