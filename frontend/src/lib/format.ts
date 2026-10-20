// Western digits (0-9) and Gregorian dates with Arabic month names.
const numberFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });
const dateFmt = new Intl.DateTimeFormat('ar-u-ca-gregory-nu-latn', { day: 'numeric', month: 'long', year: 'numeric' });
const shortDateFmt = new Intl.DateTimeFormat('ar-u-ca-gregory-nu-latn', { day: 'numeric', month: 'short' });
const dateTimeFmt = new Intl.DateTimeFormat('ar-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'short',
  hour: 'numeric',
  minute: '2-digit',
});

/** Parse "YYYY-MM-DD" as a local date (avoids the UTC off-by-one). */
export function parseDate(value: string): Date {
  const [y, m, d] = value.slice(0, 10).split('-').map(Number);
  return new Date(y, m - 1, d);
}

export function fmtNumber(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return digits === 2 ? numberFmt.format(v) : new Intl.NumberFormat('en-US', { maximumFractionDigits: digits }).format(v);
}

export function fmtInt(v: number | null | undefined): string {
  return fmtNumber(v === null || v === undefined ? v : Math.round(v), 0);
}

export function fmtSigned(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return '—';
  if (Math.abs(v) < 1e-9) return '0';
  return `${v > 0 ? '+' : '−'}${fmtNumber(Math.abs(v), digits)}`;
}

export function fmtDate(v: string | null | undefined): string {
  return v ? dateFmt.format(parseDate(v)) : '—';
}

export function fmtShortDate(v: string | null | undefined): string {
  return v ? shortDateFmt.format(parseDate(v)) : '—';
}

export function fmtDateTime(v: string | null | undefined): string {
  return v ? dateTimeFmt.format(new Date(v)) : '—';
}

export function todayISO(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function daysAgo(v: string | null | undefined): number | null {
  if (!v) return null;
  const ms = new Date().setHours(0, 0, 0, 0) - parseDate(v).getTime();
  return Math.round(ms / 86_400_000);
}

export function relativeDays(v: string | null | undefined): string {
  const n = daysAgo(v);
  if (n === null) return '—';
  if (n <= 0) return 'اليوم';
  if (n === 1) return 'أمس';
  if (n === 2) return 'قبل يومين';
  if (n <= 10) return `قبل ${n} أيام`;
  return `قبل ${n} يوماً`;
}
