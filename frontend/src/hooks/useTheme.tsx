import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

export type ThemeChoice = 'light' | 'dark' | 'system';
const KEY = 'tahadi-theme';

function readChoice(): ThemeChoice {
  try {
    const v = localStorage.getItem(KEY);
    return v === 'light' || v === 'dark' ? v : 'system';
  } catch {
    return 'system';
  }
}

function systemDark() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
}

interface ThemeContextValue {
  choice: ThemeChoice;
  isDark: boolean;
  setChoice: (c: ThemeChoice) => void;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoiceState] = useState<ThemeChoice>(readChoice);
  const [sysDark, setSysDark] = useState(systemDark);
  const isDark = choice === 'dark' || (choice === 'system' && sysDark);

  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)');
    if (!mq) return;
    const fn = () => setSysDark(mq.matches);
    mq.addEventListener('change', fn);
    return () => mq.removeEventListener('change', fn);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
  }, [isDark]);

  const setChoice = useCallback((c: ThemeChoice) => {
    setChoiceState(c);
    try {
      localStorage.setItem(KEY, c);
    } catch {
      /* ignore */
    }
  }, []);

  const toggle = useCallback(() => setChoice(isDark ? 'light' : 'dark'), [isDark, setChoice]);

  return <ThemeContext.Provider value={{ choice, isDark, setChoice, toggle }}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>');
  return ctx;
}

/** Resolved token colours for libraries that need literal colour strings (Recharts). */
export function useChartColors() {
  const { isDark } = useTheme();
  const [colors, setColors] = useState(() => readColors());
  useEffect(() => setColors(readColors()), [isDark]);
  return colors;
}

function readColors() {
  const css = getComputedStyle(document.documentElement);
  const c = (name: string) => `rgb(${css.getPropertyValue(`--c-${name}`).trim().split(/\s+/).join(',')})`;
  return {
    primary: c('primary'),
    accent: c('accent'),
    line: c('line'),
    muted: c('muted'),
    ink: c('ink'),
    surface: c('surface'),
    good: c('good'),
    bad: c('bad'),
    warn: c('warn'),
  };
}
