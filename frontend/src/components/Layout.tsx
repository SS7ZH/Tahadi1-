import clsx from 'clsx';
import {
  Calculator,
  ClipboardList,
  Dumbbell,
  History,
  LayoutDashboard,
  Link2,
  LogOut,
  MessageCircleQuestion,
  CreditCard,
  FileSignature,
  Globe,
  Home,
  Moon,
  Salad,
  SlidersHorizontal,
  Sparkles,
  Sun,
  TrendingUp,
  UserRound,
  Users,
} from 'lucide-react';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import type { Role } from '@/api/types';
import { useAuth, useCurrentUser } from '@/hooks/useAuth';
import { useInbox, useOnboarding } from '@/hooks/queries';
import { useTheme } from '@/hooks/useTheme';
import { tr } from '@/i18n';
import { LanguageSwitch } from './LanguageSwitch';
import { Logo } from './Logo';
import { CountBadge, IconButton } from './ui';

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
  badge?: number;
  /** shown in the user menu instead of the top / bottom bar */
  menu?: boolean;
}

function useNavItems(role: Role): NavItem[] {
  const inbox = useInbox('open', role !== 'client');
  const open = inbox.data?.length ?? 0;
  const ic = 'h-5 w-5';
  if (role === 'admin')
    return [
      { to: '/admin', label: tr.nav.dashboard, icon: <LayoutDashboard className={ic} />, end: true },
      { to: '/admin/users', label: tr.nav.users, icon: <Users className={ic} /> },
      { to: '/admin/assign', label: tr.nav.assign, icon: <Link2 className={ic} /> },
      { to: '/admin/questions', label: tr.nav.inbox, icon: <MessageCircleQuestion className={ic} />, badge: open },
      { to: '/admin/settings', label: tr.nav.settings, icon: <SlidersHorizontal className={ic} /> },
      { to: '/admin/exercises', label: tr.nav.exercises, icon: <Dumbbell className={ic} />, menu: true },
      { to: '/admin/plans', label: tr.nav.plans, icon: <CreditCard className={ic} />, menu: true },
      { to: '/admin/templates', label: tr.nav.templates, icon: <FileSignature className={ic} />, menu: true },
      { to: '/admin/site', label: tr.nav.siteContent, icon: <Globe className={ic} />, menu: true },
      { to: '/demo', label: 'المساعد الذكي (AI)', icon: <Sparkles className={ic} />, menu: true },
      { to: '/calculator', label: tr.nav.calculator, icon: <Calculator className={ic} />, menu: true },
    ];
  if (role === 'trainer')
    return [
      { to: '/trainer', label: tr.nav.trainerHome, icon: <Users className={ic} />, end: true },
      { to: '/demo', label: 'المساعد الذكي (AI)', icon: <Sparkles className={ic} /> },
      { to: '/trainer/questions', label: tr.nav.inbox, icon: <MessageCircleQuestion className={ic} />, badge: open },
      { to: '/calculator', label: tr.nav.calculator, icon: <Calculator className={ic} /> },
      { to: '/profile', label: tr.nav.profile, icon: <UserRound className={ic} /> },
    ];
  return [
    { to: '/me', label: tr.nav.home, icon: <Home className={ic} />, end: true },
    { to: '/me/progress', label: tr.nav.myProgress, icon: <TrendingUp className={ic} /> },
    { to: '/me/program', label: tr.nav.myProgram, icon: <ClipboardList className={ic} /> },
    { to: '/me/nutrition', label: tr.nav.myNutrition, icon: <Salad className={ic} /> },
    { to: '/me/ask', label: tr.nav.ask, icon: <MessageCircleQuestion className={ic} /> },
    { to: '/me/history', label: tr.nav.myHistory, icon: <History className={ic} />, menu: true },
    { to: '/me/documents', label: tr.nav.myDocuments, icon: <FileSignature className={ic} />, menu: true },
    { to: '/calculator', label: tr.nav.calculator, icon: <Calculator className={ic} />, menu: true },
  ];
}

function UserMenu({ extra }: { extra: NavItem[] }) {
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
          <span className="block text-[11px] text-muted">{tr.roles[user.role]}</span>
        </span>
      </button>
      {open && (
        <div role="menu" className="absolute end-0 top-full z-40 mt-2 w-52 overflow-hidden rounded-2xl border border-line bg-surface p-1 shadow-xl">
          {extra.map((item) => (
            <Link key={item.to} role="menuitem" to={item.to} className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-surface-2 [&_svg]:h-4 [&_svg]:w-4 [&_svg]:text-muted">
              {item.icon}
              {item.label}
            </Link>
          ))}
          <Link role="menuitem" to="/profile" className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-surface-2">
            <UserRound className="h-4 w-4 text-muted" />
            {tr.nav.profile}
          </Link>
          {!extra.some((i) => i.to === '/calculator') && (
            <Link role="menuitem" to="/calculator" className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-surface-2">
              <Calculator className="h-4 w-4 text-muted" />
              {tr.nav.calculator}
            </Link>
          )}
          <button
            role="menuitem"
            type="button"
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-bad hover:bg-bad/10"
          >
            <LogOut className="h-4 w-4" />
            {tr.nav.logout}
          </button>
        </div>
      )}
    </div>
  );
}

function ExpiredBanner() {
  const status = useOnboarding();
  if (status.data?.subscription?.status !== 'expired') return null;
  return (
    <div role="status" className="border-b border-bad/30 bg-bad/10 px-4 py-2.5 text-center text-sm font-semibold text-bad">
      {tr.documents.expiredBanner}
    </div>
  );
}

export function Layout() {
  const user = useCurrentUser();
  const all = useNavItems(user.role);
  const items = all.filter((i) => !i.menu);
  const menuItems = all.filter((i) => i.menu);
  const { isDark, toggle } = useTheme();
  // Mobile bottom bar fits 5 items comfortably.
  const mobileItems = items.slice(0, 5);

  return (
    <div className="min-h-screen pb-[calc(4.5rem+env(safe-area-inset-bottom))] md:pb-0">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
          <Link to="/" className="shrink-0" aria-label={tr.brand}>
            <Logo />
          </Link>
          <nav className="hidden flex-1 items-center gap-1 md:flex" aria-label={tr.nav.menu}>
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
            <LanguageSwitch compact />
            <IconButton label={tr.theme.toggle} onClick={toggle}>
              {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </IconButton>
            <UserMenu extra={menuItems} />
          </div>
        </div>
      </header>

      {user.role === 'client' && <ExpiredBanner />}
      <main className="mx-auto max-w-6xl px-4 py-5 sm:py-7">
        <Outlet />
      </main>

      <nav
        aria-label={tr.nav.menu}
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
