import clsx from 'clsx';
import { ar } from '@/i18n/ar';

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={clsx('h-9 w-9', className)} aria-hidden>
      <rect width="64" height="64" rx="16" className="fill-primary" />
      <path
        d="M14 44 L26 30 L34 38 L50 18"
        fill="none"
        stroke="white"
        strokeWidth="6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="50" cy="18" r="5" fill="white" />
    </svg>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={clsx('inline-flex items-center gap-2', className)}>
      <LogoMark />
      <span className="text-xl font-bold tracking-tight">{ar.brand}</span>
    </span>
  );
}
