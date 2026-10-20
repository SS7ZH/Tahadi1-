import clsx from 'clsx';
import {
  Calculator,
  History,
  LayoutDashboard,
  Link2,
  LogOut,
  MessageCircleQuestion,
  Moon,
  SlidersHorizontal,
  Sun,
  TrendingUp,
  UserRound,
  Users,
} from 'lucide-react';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import type { Role } from '@/api/types';
import { useAuth, useCurrentUser, homePathFor } from '@/hooks/useAuth';
import { useInbox } from '@/hooks/queries';
import { useTheme } from '@/hooks/useTheme';
import { ar } from '@/i18n/ar';
import { Logo } from './Logo';
import { CountBadge, IconButton } from './ui';

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
  badge?: number;
}

function useNavItems(role: Role): NavItem[] {
  const inbox = useInbox('open', role !== 'client');
  const open = inbox.data?.length ?? 0;
  const ic = 'h-5 w-5';
  if (role === 'admin')
    return [
      { to: '/admin', label: ar.nav.dashboard, icon: <LayoutDashboard className={ic} />, end: true },
      { to: '/admin/users', label: ar.nav.users, icon: <Users className={ic} /> },
      { to: '/admin/assign', label: ar.nav.assign, icon: <Link2 className={ic} /> },
      { to: '/admin/questions', label: ar.nav.inbox, icon: <MessageCircleQuestion className={ic} />, badge: open },
      { to: '/admin/settings', label: ar.nav.settings, icon: <SlidersHorizontal className={ic} /> },
      { to: '/calculator', label: ar.nav.calculator, icon: <Calculator className={ic} /> },
    ];
  if (role === 'trainer')
    return [
      { to: '/trainer', label: ar.nav.trainerHome, icon: <Users className={ic} />, end: true },
      { to: '/trainer/questions', label: ar.nav.inbox, icon: <MessageCircleQuestion className={ic} />, badge: open },
      { to: '/calculator', label: ar.nav.calculator, icon: <Calculator className={ic} /> },
      { to: '/profile', label: ar.nav.profile, icon: <UserRound className={ic} /> },
    ];
  return [
    { to: '/me', label: ar.nav.myProgress, icon: <TrendingUp className={ic} />, end: true },
    { to: '/me/history', label: ar.nav.myHistory, icon: <History className={ic} /> },
    { to: '/me/ask', label: ar.nav.ask, icon: <MessageCircleQuestion className={ic} /> },
    { to: '/calculator', label: ar.nav.calculator, icon: <Calculator className={ic} /> },
    { to: '/profile', label: ar.nav.profile, icon: <UserRound className={ic} /> },
  ];
}

function UserMenu() {
  const user = useCurrentUser();
  const { logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();
  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="flex items-center gap-2 rounded-xl px-1.5 py-1 transition hover:bg-surface-2"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/15 text-sm font-bold text-accent">
          {user.full_name.trim().charAt(0)}
        </span>
        <span className="hidden text-start leading-tight sm:block">
          <span className="block max-w-[10rem] truncate text-sm font-semibold">{user.full_name}</span>
          <span className="block text-[11px] text-muted">{ar.roles[user.role]}</span>
        </span>
      </button>
      {open && (
        <div role="menu" className="absolute end-0 top-full z-40 mt-2 w-52 overflow-hidden rounded-2xl border border-line bg-surface p-1 shadow-xl">
          <Link role="menuitem" to="/profile" className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-surface-2">
            <UserRound className="h-4 w-4 text-muted" />
            {ar.nav.profile}
          </Link>
          <Link role="menuitem" to="/calculator" className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-surface-2">
            <Calculator className="h-4 w-4 text-muted" />
            {ar.nav.calculator}
          </Link>
          <button
            role="menuitem"
            type="button"
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-bad hover:bg-bad/10"
          >
            <LogOut className="h-4 w-4" />
            {ar.nav.logout}
          </button>
        </div>
      )}
    </div>
  );
}

export function Layout() {
  const user = useCurrentUser();
  const items = useNavItems(user.role);
  const { isDark, toggle } = useTheme();
  // Mobile bottom bar fits 5 items comfortably.
  const mobileItems = items.slice(0, 5);

  return (
    <div className="min-h-screen pb-[calc(4.5rem+env(safe-area-inset-bottom))] md:pb-0">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
          <Link to={homePathFor(user.role)} className="shrink-0">
            <Logo />
          </Link>
          <nav className="hidden flex-1 items-center gap-1 md:flex" aria-label={ar.nav.menu}>
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  clsx(
                    'inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold transition',
                    isActive ? 'bg-primary/10 text-primary' : 'text-muted hover:bg-surface-2 hover:text-ink',
                  )
                }
              >
                {item.label}
                <CountBadge count={item.badge ?? 0} />
              </NavLink>
            ))}
          </nav>
          <div className="ms-auto flex items-center gap-1">
            <IconButton label={ar.theme.toggle} onClick={toggle}>
              {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </IconButton>
            <UserMenu />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-5 sm:py-7">
        <Outlet />
      </main>

      <nav
        aria-label={ar.nav.menu}
        className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
      >
        <div className="mx-auto flex max-w-lg">
          {mobileItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                clsx(
                  'relative flex flex-1 flex-col items-center gap-0.5 px-1 pb-2 pt-2.5 text-[11px] font-semibold transition',
                  isActive ? 'text-primary' : 'text-muted',
                )
              }
            >
              <span className="relative">
                {item.icon}
                {!!item.badge && (
                  <span className="absolute -end-2 -top-1.5">
                    <CountBadge count={item.badge} />
                  </span>
                )}
              </span>
              <span className="max-w-full truncate">{item.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
