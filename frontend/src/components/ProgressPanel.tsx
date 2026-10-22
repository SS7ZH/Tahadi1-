import { ArrowLeftRight, FileDown, LineChart as LineChartIcon } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { errorMessage } from '@/api/client';
import { CATEGORIES, type Progress, type Session } from '@/api/types';
import { useProgress, useSessions } from '@/hooks/queries';
import { useChartColors } from '@/hooks/useTheme';
import { loc, tr, useLang } from '@/i18n';
import { fmtDate, fmtNumber, fmtShortDate } from '@/lib/format';
import { trendOf } from '@/lib/trend';
import { ExportMeasurementsModal } from './ExportMeasurementsModal';
import { TrendChip } from './TrendChip';
import { Button, Card, CardHeader, EmptyState, ErrorState, Select, Skeleton } from './ui';

function MetricSelect({ progress, value, onChange }: { progress: Progress; value: string; onChange: (k: string) => void }) {
  return (
    <Select label={tr.progress.metric} value={value} onChange={(e) => onChange(e.target.value)} wrapperClassName="w-full sm:w-72">
      {CATEGORIES.map((cat) => {
        const opts = progress.available.filter((a) => a.category === cat);
        if (!opts.length) return null;
        return (
          <optgroup key={cat} label={tr.categories[cat]}>
            {opts.map((o) => {
              const n = progress.series[o.key]?.points.length ?? 0;
              return (
                <option key={o.key} value={o.key} disabled={n === 0}>
                  {loc(o.name_ar, o.name_en)}
                  {o.derived ? ` (${tr.progress.derived})` : ''}
                  {n === 0 ? ' —' : ''}
                </option>
              );
            })}
          </optgroup>
        );
      })}
    </Select>
  );
}

function ProgressChart({ progress, metric }: { progress: Progress; metric: string }) {
  const colors = useChartColors();
  const { isRtl } = useLang();
  const series = progress.series[metric];
  const isBp = metric === 'blood_pressure';
  const data = useMemo(
    () =>
      (series?.points ?? []).map((p) => ({
        label: fmtShortDate(p.date),
        fullDate: fmtDate(p.date),
        value: p.value,
        diastolic: p.diastolic,
      })),
    [series],
  );

  if (!series || series.points.length === 0)
    return <EmptyState icon={<LineChartIcon className="h-6 w-6" />} title={tr.progress.notEnough} description={tr.progress.notEnoughHint} />;

  const unit = loc(series.unit, series.unit_en);
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: tr.progress.first, value: series.first },
          { label: tr.progress.latest, value: series.latest },
        ].map((s) => (
          <div key={s.label} className="rounded-xl bg-surface-2 px-3 py-2.5">
            <p className="text-[11px] text-muted">{s.label}</p>
            <p className="mt-0.5 font-bold">
              <span className="num">{fmtNumber(s.value)}</span>
              {unit && <span className="ms-1 text-xs font-normal text-muted">{unit}</span>}
            </p>
          </div>
        ))}
        <div className="rounded-xl bg-surface-2 px-3 py-2.5">
          <p className="text-[11px] text-muted">{tr.progress.change}</p>
          <div className="mt-1">
            <TrendChip change={series.change} trend={series.trend} />
          </div>
        </div>
      </div>

      {/* Time flows with the reading direction: in Arabic the earliest date is on the right and the Y axis on the right. */}
      <div className="h-64 w-full sm:h-80" role="img" aria-label={`${tr.progress.chartTitle}: ${loc(series.name_ar, series.name_en)}`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 4, left: 4, bottom: 0 }}>
            <CartesianGrid stroke={colors.line} strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              reversed={isRtl}
              tick={{ fill: colors.muted, fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: colors.line }}
              minTickGap={16}
            />
            <YAxis
              orientation={isRtl ? 'right' : 'left'}
              domain={['auto', 'auto']}
              tick={{ fill: colors.muted, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={44}
              tickFormatter={(v: number) => fmtNumber(v, 1)}
            />
            <Tooltip
              contentStyle={{
                background: colors.surface,
                border: `1px solid ${colors.line}`,
                borderRadius: 12,
                color: colors.ink,
                fontFamily: 'inherit',
              }}
              labelFormatter={(_, payload) => (payload?.[0]?.payload as { fullDate?: string } | undefined)?.fullDate ?? ''}
              formatter={(value: number, name: string) => [`${fmtNumber(value)} ${unit}`, name]}
            />
            {isBp && <Legend wrapperStyle={{ fontSize: 12 }} />}
            <Line
              type="monotone"
              dataKey="value"
              name={isBp ? tr.progress.systolic : loc(series.name_ar, series.name_en)}
              stroke={colors.primary}
              strokeWidth={2.5}
              dot={{ r: 3.5, fill: colors.primary, strokeWidth: 0 }}
              activeDot={{ r: 6 }}
              isAnimationActive={false}
            />
            {isBp && (
              <Line
                type="monotone"
                dataKey="diastolic"
                name={tr.progress.diastolic}
                stroke={colors.accent}
                strokeWidth={2.5}
                dot={{ r: 3.5, fill: colors.accent, strokeWidth: 0 }}
                isAnimationActive={false}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function sessionLabel(s: Session) {
  return fmtDate(s.session_date);
}

function ComparePanel({ progress, sessions }: { progress: Progress; sessions: Session[] }) {
  const ordered = useMemo(() => [...sessions].sort((a, b) => a.session_date.localeCompare(b.session_date)), [sessions]);
  const [beforeId, setBeforeId] = useState<number | null>(null);
  const [afterId, setAfterId] = useState<number | null>(null);

  useEffect(() => {
    if (ordered.length >= 2) {
      setBeforeId((v) => v ?? ordered[0].id);
      setAfterId((v) => v ?? ordered[ordered.length - 1].id);
    }
  }, [ordered]);

  if (ordered.length < 2) return <p className="p-5 text-sm text-muted">{tr.progress.needTwo}</p>;

  const rows = Object.values(progress.series)
    .map((s) => {
      const b = s.points.find((p) => p.session_id === beforeId);
      const a = s.points.find((p) => p.session_id === afterId);
      if (!a && !b) return null;
      const diff = a && b ? a.value - b.value : null;
      const fmtVal = (p?: { value: number; diastolic?: number }) =>
        p ? (p.diastolic !== undefined ? `${p.value}/${p.diastolic}` : fmtNumber(p.value)) : '—';
      return { key: s.key, name: loc(s.name_ar, s.name_en), unit: loc(s.unit, s.unit_en), before: fmtVal(b), after: fmtVal(a), diff, trend: trendOf(s.better_direction, diff) };
    })
    .filter((r): r is NonNullable<typeof r> => r !== null);

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-5">
      <div className="grid grid-cols-2 gap-3">
        <Select label={tr.progress.before} value={beforeId ?? ''} onChange={(e) => setBeforeId(Number(e.target.value))}>
          {ordered.map((s) => (
            <option key={s.id} value={s.id}>
              {sessionLabel(s)}
            </option>
          ))}
        </Select>
        <Select label={tr.progress.after} value={afterId ?? ''} onChange={(e) => setAfterId(Number(e.target.value))}>
          {ordered.map((s) => (
            <option key={s.id} value={s.id}>
              {sessionLabel(s)}
            </option>
          ))}
        </Select>
      </div>
      <div className="-mx-4 overflow-x-auto sm:mx-0">
        <table className="w-full min-w-[22rem] text-sm">
          <thead>
            <tr className="border-b border-line text-xs text-muted">
              <th className="px-4 py-2 text-start font-medium sm:px-2">{tr.progress.metric}</th>
              <th className="px-2 py-2 text-start font-medium">{tr.progress.before}</th>
              <th className="px-2 py-2 text-start font-medium">{tr.progress.after}</th>
              <th className="px-4 py-2 text-start font-medium sm:px-2">{tr.progress.difference}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((r) => (
              <tr key={r.key}>
                <td className="px-4 py-2.5 font-medium sm:px-2">
                  {r.name}
                  {r.unit && <span className="ms-1 text-[11px] text-muted">({r.unit})</span>}
                </td>
                <td className="num px-2 py-2.5 text-start text-muted">{r.before}</td>
                <td className="num px-2 py-2.5 text-start font-semibold">{r.after}</td>
                <td className="px-4 py-2.5 sm:px-2">
                  {r.diff !== null ? <TrendChip change={Math.round(r.diff * 100) / 100} trend={r.trend} /> : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ProgressPanel({ clientId }: { clientId: number }) {
  const progress = useProgress(clientId);
  const sessions = useSessions(clientId);
  const [metric, setMetric] = useState('weight');
  const [exportOpen, setExportOpen] = useState(false);

  // Fall back to the first metric that has data.
  useEffect(() => {
    const p = progress.data;
    if (p && !p.series[metric]?.points.length) {
      const first = p.available.find((a) => p.series[a.key]?.points.length);
      if (first) setMetric(first.key);
    }
  }, [progress.data, metric]);

  if (progress.isLoading) return <Skeleton className="h-96" />;
  if (progress.error) return <ErrorState message={errorMessage(progress.error)} onRetry={() => progress.refetch()} />;
  if (!progress.data) return null;

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          title={tr.progress.chartTitle}
          icon={<LineChartIcon className="h-5 w-5" />}
          actions={
            <Button
              variant="outline"
              size="sm"
              icon={<FileDown className="h-4 w-4" />}
              onClick={() => setExportOpen(true)}
            >
              {tr.pdf.exportPdf}
            </Button>
          }
        />
        <div className="flex flex-col gap-4 p-4 sm:p-5">
          <MetricSelect progress={progress.data} value={metric} onChange={setMetric} />
          <ProgressChart progress={progress.data} metric={metric} />
        </div>
      </Card>
      <Card>
        <CardHeader title={tr.progress.compare} subtitle={tr.progress.compareHint} icon={<ArrowLeftRight className="h-5 w-5" />} />
        {sessions.data ? <ComparePanel progress={progress.data} sessions={sessions.data} /> : <Skeleton className="m-5 h-40" />}
      </Card>
      <ExportMeasurementsModal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        clientId={clientId}
      />
    </div>
  );
}
