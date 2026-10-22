import { Fragment, useSyncExternalStore, type ReactNode } from 'react';
import { ar, type Messages } from './ar';
import { en } from './en';

export type Lang = 'ar' | 'en';
export type { Messages };

const STORAGE_KEY = 'tahadi-lang';
const catalogs: Record<Lang, Messages> = { ar, en };

function readStored(): Lang {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'ar';
  } catch {
    return 'ar';
  }
}

let current: Lang = readStored();
const listeners = new Set<() => void>();

function applyToDocument() {
  if (typeof document === 'undefined') return;
  document.documentElement.lang = current;
  document.documentElement.dir = current === 'ar' ? 'rtl' : 'ltr';
  document.title = catalogs[current].brand;
}
applyToDocument();

export function getLang(): Lang {
  return current;
}

export function setLang(lang: Lang) {
  if (lang === current) return;
  current = lang;
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* private mode: in-memory only */
  }
  applyToDocument();
  listeners.forEach((fn) => fn());
}

function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

/**
 * Live message catalog: `tr.common.save` always reads the current language.
 * Components re-render on a language change because <LanguageBoundary> remounts the app subtree.
 * Do not read `tr` at module load time (e.g. in a top-level constant); read it inside functions/components.
 */
export const tr: Messages = new Proxy({} as Messages, {
  get: (_target, prop) => (catalogs[current] as unknown as Record<string | symbol, unknown>)[prop],
});

/** Pick a localized API field (e.g. name_ar / name_en), falling back to whichever exists. */
export function loc(arValue: string | null | undefined, enValue: string | null | undefined): string {
  return (current === 'en' ? enValue || arValue : arValue || enValue) ?? '';
}

export function useLang() {
  const lang = useSyncExternalStore(subscribe, getLang, getLang);
  return {
    lang,
    isRtl: lang === 'ar',
    dir: (lang === 'ar' ? 'rtl' : 'ltr') as 'rtl' | 'ltr',
    setLang,
    toggle: () => setLang(lang === 'ar' ? 'en' : 'ar'),
  };
}

/** Remounts its children when the language changes so every `tr.*` read refreshes. */
export function LanguageBoundary({ children }: { children: ReactNode }) {
  const { lang } = useLang();
  return <Fragment key={lang}>{children}</Fragment>;
}
