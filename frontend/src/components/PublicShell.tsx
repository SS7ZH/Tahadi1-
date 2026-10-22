import { LayoutDashboard, LogIn, Moon, Sun } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { homePathFor, useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/hooks/useTheme';
import { tr } from '@/i18n';
import { LanguageSwitch } from './LanguageSwitch';
import { Logo } from './Logo';
import { Button, IconButton } from './ui';

/** Header + footer for public pages (home page, calculator for visitors). */
export function PublicShell({ children }: { children?: ReactNode }) {
  const { user } = useAuth();
  const { isDark, toggle } = useTheme();
  const { pathname } = useLocation();
  const anchor = (id: string) => (pathname === '/' ? `#${id}` : `/#${id}`);
  const links = [
    { href: anchor('features'), label: tr.landing.navFeatures },
    { href: anchor('how'), label: tr.landing.navHow },
    { href: anchor('plans'), label: tr.landing.navPlans },
    { href: anchor('contact'), label: tr.landing.navContact },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4">
          <Link to="/" className="shrink-0" aria-label={tr.brand}>
            <Logo />
          </Link>
          <nav className="hidden flex-1 items-center gap-1 md:flex" aria-label={tr.nav.menu}>
            {links.map((l) => (
              <a key={l.href} href={l.href} className="rounded-xl px-3 py-2 text-sm font-semibold text-muted transition hover:bg-surface-2 hover:text-ink">
                {l.label}
              </a>
            ))}
            <Link to="/calculator" className="rounded-xl px-3 py-2 text-sm font-semibold text-muted transition hover:bg-surface-2 hover:text-ink">
              {tr.nav.calculator}
            </Link>
          </nav>
          <div className="ms-auto flex items-center gap-1">
            <LanguageSwitch compact />
            <IconButton label={tr.theme.toggle} onClick={toggle}>
              {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </IconButton>
            {user ? (
              <Link to={homePathFor(user.role)}>
                <Button size="sm" icon={<LayoutDashboard className="h-4 w-4" />}>
                  {tr.landing.myDashboard}
                </Button>
              </Link>
            ) : (
              <Link to="/login">
                <Button size="sm" icon={<LogIn className="h-4 w-4 rtl:-scale-x-100" />}>
                  {tr.landing.login}
                </Button>
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">{children ?? <Outlet />}</main>

      <footer className="border-t border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-6 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <Logo className="[&_span]:text-base" />
            <span className="hidden sm:inline">· {tr.tagline}</span>
          </div>
          <nav className="flex flex-wrap gap-x-4 gap-y-1" aria-label={tr.nav.menu}>
            {links.map((l) => (
              <a key={l.href} href={l.href} className="hover:text-ink">
                {l.label}
              </a>
            ))}
            <Link to="/calculator" className="hover:text-ink">
              {tr.nav.calculator}
            </Link>
          </nav>
          <p>{tr.landing.rights(new Date().getFullYear())}</p>
        </div>
      </footer>
    </div>
  );
}
