// Western digits (0-9) in both languages; Gregorian dates with Arabic or English month names.
import { getLang, tr } from '@/i18n';

const numberFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });
const LOCALES = { ar: 'ar-u-ca-gregory-nu-latn', en: 'en-GB' } as const;
const dateFormatters = new Map<string, Intl.DateTimeFormat>();

function dateFormatter(kind: 'long' | 'short' | 'time'): Intl.DateTimeFormat {
  const lang = getLang();
  const key = `${lang}:${kind}`;
  let f = dateFormatters.get(key);
  if (!f) {
    const opts: Intl.DateTimeFormatOptions =
      kind === 'long'
        ? { day: 'numeric', month: 'long', year: 'numeric' }
        : kind === 'short'
          ? { day: 'numeric', month: 'short' }
          : { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' };
    f = new Intl.DateTimeFormat(LOCALES[lang], opts);
    dateFormatters.set(key, f);
  }
  return f;
}

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
  return v ? dateFormatter('long').format(parseDate(v)) : '—';
}

export function fmtShortDate(v: string | null | undefined): string {
  return v ? dateFormatter('short').format(parseDate(v)) : '—';
}

export function fmtDateTime(v: string | null | undefined): string {
  return v ? dateFormatter('time').format(new Date(v)) : '—';
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
  if (n <= 0) return tr.time.today;
  if (n === 1) return tr.time.yesterday;
  if (n === 2) return tr.time.twoDaysAgo;
  return tr.time.daysAgo(n);
}
