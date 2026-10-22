import clsx from 'clsx';
import { Languages } from 'lucide-react';
import { tr, useLang } from '@/i18n';

/** Toggles Arabic ⇄ English. Shows the language you would switch *to*. */
export function LanguageSwitch({ className, compact }: { className?: string; compact?: boolean }) {
  const { toggle } = useLang();
  return (
    <button
      type="button"
      onClick={toggle}
      title={tr.lang.label}
      aria-label={`${tr.lang.label}: ${tr.lang.switchTo}`}
      className={clsx(
        'inline-flex h-9 items-center gap-1.5 rounded-xl px-2.5 text-sm font-semibold text-muted transition hover:bg-surface-2 hover:text-ink',
        className,
      )}
    >
      <Languages className="h-4 w-4" />
      <span>{compact ? tr.lang.switchToShort : tr.lang.switchTo}</span>
    </button>
  );
}
