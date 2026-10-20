import { useQueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { onAuthFailure, refreshTokens, tokens } from '@/api/client';
import { authApi } from '@/api/endpoints';
import type { Role, User } from '@/api/types';

type Status = 'loading' | 'authenticated' | 'anonymous';

interface AuthContextValue {
  user: User | null;
  status: Status;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
  setUser: (u: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function homePathFor(role: Role): string {
  return role === 'admin' ? '/admin' : role === 'trainer' ? '/trainer' : '/me';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<Status>(tokens.refresh ? 'loading' : 'anonymous');

  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
    setStatus('anonymous');
    queryClient.clear();
  }, [queryClient]);

  // Restore the session from the stored refresh token on first load.
  useEffect(() => {
    onAuthFailure(() => {
      setUser(null);
      setStatus('anonymous');
      queryClient.clear();
    });
    if (!tokens.refresh) return;
    let cancelled = false;
    refreshTokens()
      .then((pair) => {
        if (cancelled) return;
        setUser(pair.user);
        setStatus('authenticated');
      })
      .catch(() => {
        if (cancelled) return;
        tokens.clear();
        setStatus('anonymous');
      });
    return () => {
      cancelled = true;
    };
  }, [queryClient]);

  const login = useCallback(async (email: string, password: string) => {
    const pair = await authApi.login(email, password);
    tokens.set(pair);
    setUser(pair.user);
    setStatus('authenticated');
    return pair.user;
  }, []);

  const value = useMemo(() => ({ user, status, login, logout, setUser }), [user, status, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}

/** For components that only render inside protected routes. */
export function useCurrentUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error('No authenticated user');
  return user;
}
