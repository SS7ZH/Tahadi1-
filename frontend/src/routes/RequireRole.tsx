import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import type { Role } from '@/api/types';
import { LogoMark } from '@/components/Logo';
import { Spinner } from '@/components/ui';
import { homePathFor, useAuth } from '@/hooks/useAuth';

export function FullScreenLoader() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <LogoMark className="h-12 w-12" />
      <Spinner />
    </div>
  );
}

/** UI-level guard. The real enforcement is on the API: hidden routes are a convenience, not security. */
export function RequireRole({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { user, status } = useAuth();
  const location = useLocation();
  if (status === 'loading') return <FullScreenLoader />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to={homePathFor(user.role)} replace />;
  return <>{children}</>;
}
