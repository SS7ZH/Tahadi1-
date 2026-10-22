import clsx from 'clsx';
import { Calendar, CheckSquare, FileDown, MessageSquare } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { useProgress } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { downloadPdf } from '@/lib/download';
import { Button, Input, Modal } from './ui';

interface ExportMeasurementsModalProps {
  open: boolean;
  onClose: () => void;
  clientId: number;
}

const DEFAULT_KEYS = ['weight', 'waist', 'body_fat'];
const MAX_METRICS = 8;

export function ExportMeasurementsModal({ open, onClose, clientId }: ExportMeasurementsModalProps) {
  const progress = useProgress(clientId);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [selectedKeys, setSelectedKeys] = useState<string[]>(DEFAULT_KEYS);
  const [comments, setComments] = useState(true);
  const [exporting, setExporting] = useState(false);

  // Initialize selected keys from available if default keys aren't present
  useEffect(() => {
    if (progress.data?.available?.length) {
      const avail = progress.data.available.map((a) => a.key);
      const match = DEFAULT_KEYS.filter((k) => avail.includes(k));
      if (match.length > 0) {
        setSelectedKeys(match);
      } else {
        setSelectedKeys(avail.slice(0, 3));
      }
    }
  }, [progress.data]);

  const toggleKey = (key: string) => {
    if (selectedKeys.includes(key)) {
      setSelectedKeys(selectedKeys.filter((k) => k !== key));
    } else {
      if (selectedKeys.length >= MAX_METRICS) {
        toast.warning(tr.pdf.selectedCount(MAX_METRICS));
        return;
      }
      setSelectedKeys([...selectedKeys, key]);
    }
  };

  const setPreset = (days: number | null) => {
    if (days === null) {
      setDateFrom('');
      setDateTo('');
      return;
    }
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - days);
    const toISO = (d: Date) => d.toISOString().slice(0, 10);
    setDateFrom(toISO(start));
    setDateTo(toISO(end));
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const params: Record<string, unknown> = {
        comments,
      };
      if (dateFrom) params.from = dateFrom;
      if (dateTo) params.to = dateTo;
      if (selectedKeys.length > 0) params.keys = selectedKeys.join(',');

      await downloadPdf(`/pdf/measurements/${clientId}`, { params });
      toast.success(tr.pdf.exported);
      onClose();
    } catch (err) {
      toast.error(errorMessage(err) || tr.pdf.exportFailed);
    } finally {
      setExporting(false);
    }
  };

  const available = progress.data?.available ?? [];

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={tr.pdf.measurementsExport}
      size="md"
      footer={
        <div className="flex w-full items-center justify-between gap-2">
          <Button variant="ghost" onClick={onClose} disabled={exporting}>
            {tr.common.cancel}
          </Button>
          <Button
            icon={<FileDown className="h-4 w-4" />}
            loading={exporting}
            onClick={handleExport}
          >
            {tr.pdf.exportPdf}
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-5">
        <p className="text-xs text-muted">{tr.pdf.measurementsSubtitle}</p>

        {/* Date range section */}
        <div className="flex flex-col gap-2 rounded-xl bg-surface-2 p-3.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold">
            <Calendar className="h-4 w-4 text-primary" />
            <span>{tr.pdf.dateRange}</span>
          </div>
          <div className="flex flex-wrap gap-1.5 pt-1">
            <button
              type="button"
              onClick={() => setPreset(null)}
              className={clsx(
                'rounded-lg px-2.5 py-1 text-xs font-medium transition',
                !dateFrom && !dateTo ? 'bg-primary text-on-primary' : 'bg-surface border border-line hover:bg-surface-2',
              )}
            >
              {tr.pdf.allDates}
            </button>
            <button
              type="button"
              onClick={() => setPreset(30)}
              className={clsx(
                'rounded-lg px-2.5 py-1 text-xs font-medium transition',
                dateFrom && dateTo ? 'bg-surface border border-line hover:bg-surface-2' : 'bg-surface border border-line hover:bg-surface-2',
              )}
            >
              {tr.pdf.last30Days}
            </button>
            <button
              type="button"
              onClick={() => setPreset(90)}
              className="rounded-lg border border-line bg-surface px-2.5 py-1 text-xs font-medium hover:bg-surface-2 transition"
            >
              {tr.pdf.last90Days}
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2 pt-1">
            <Input
              type="date"
              label={tr.pdf.dateFrom}
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
            <Input
              type="date"
              label={tr.pdf.dateTo}
              value={dateTo}
              min={dateFrom || undefined}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
        </div>

        {/* Metrics selection */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold">{tr.pdf.selectMetrics}</span>
            <span className={clsx('font-medium', selectedKeys.length >= MAX_METRICS ? 'text-primary font-bold' : 'text-muted')}>
              {tr.pdf.selectedCount(selectedKeys.length)}
            </span>
          </div>
          <div className="grid max-h-48 grid-cols-2 gap-1.5 overflow-y-auto rounded-xl border border-line p-2">
            {available.length > 0 ? (
              available.map((m) => {
                const checked = selectedKeys.includes(m.key);
                const disabled = !checked && selectedKeys.length >= MAX_METRICS;
                return (
                  <label
                    key={m.key}
                    className={clsx(
                      'flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition cursor-pointer select-none',
                      checked ? 'bg-primary/10 font-medium text-primary' : 'hover:bg-surface-2 text-ink',
                      disabled && 'opacity-50 cursor-not-allowed',
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={() => toggleKey(m.key)}
                      className="h-3.5 w-3.5 rounded accent-[rgb(var(--c-primary))]"
                    />
                    <span className="truncate">{loc(m.name_ar, m.name_en)}</span>
                  </label>
                );
              })
            ) : (
              <p className="col-span-2 p-2 text-center text-xs text-muted">
                <CheckSquare className="mx-auto mb-1 h-4 w-4" />
                {tr.sessions.empty}
              </p>
            )}
          </div>
        </div>

        {/* Comments checkbox */}
        <label className="flex cursor-pointer items-center gap-2.5 rounded-xl border border-line p-3 transition hover:bg-surface-2">
          <input
            type="checkbox"
            checked={comments}
            onChange={(e) => setComments(e.target.checked)}
            className="h-4 w-4 rounded accent-[rgb(var(--c-primary))]"
          />
          <MessageSquare className="h-4 w-4 text-primary" />
          <span className="text-xs font-medium">{tr.pdf.includeComments}</span>
        </label>
      </div>
    </Modal>
  );
}
