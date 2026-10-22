import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { getLang, tr } from '@/i18n';
import type { ApiErrorBody, TokenPair } from './types';

export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '');

/* ------------------------------------------------------------------
 * Token storage
 * The frontend (vercel.app) and API (onrender.com) are on different domains, so cookies
 * would need SameSite=None. We instead keep the access token in memory only and the
 * refresh token in memory + localStorage, and send the access token as a Bearer header.
 * ------------------------------------------------------------------ */
const REFRESH_KEY = 'tahadi-refresh';
let accessToken: string | null = null;
let refreshToken: string | null = null;

function readStoredRefresh(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

export const tokens = {
  get access() {
    return accessToken;
  },
  get refresh() {
    return refreshToken ?? readStoredRefresh();
  },
  set(pair: Pick<TokenPair, 'access_token' | 'refresh_token'>) {
    accessToken = pair.access_token;
    refreshToken = pair.refresh_token;
    try {
      localStorage.setItem(REFRESH_KEY, pair.refresh_token);
    } catch {
      /* private mode: in-memory only */
    }
  },
  clear() {
    accessToken = null;
    refreshToken = null;
    try {
      localStorage.removeItem(REFRESH_KEY);
    } catch {
      /* ignore */
    }
  },
};

/* ------------------------------------------------------------------
 * "Server waking up" indicator (Render free plan sleeps when idle)
 * ------------------------------------------------------------------ */
const SLOW_MS = 3000;
let slowCount = 0;
const wakeListeners = new Set<() => void>();
export const serverWake = {
  get isWaking() {
    return slowCount > 0;
  },
  subscribe(fn: () => void) {
    wakeListeners.add(fn);
    return () => wakeListeners.delete(fn);
  },
};
function emitWake() {
  wakeListeners.forEach((fn) => fn());
}
function trackSlow<T>(promise: Promise<T>): Promise<T> {
  let flagged = false;
  const timer = setTimeout(() => {
    flagged = true;
    slowCount += 1;
    emitWake();
  }, SLOW_MS);
  return promise.finally(() => {
    clearTimeout(timer);
    if (flagged) {
      slowCount -= 1;
      emitWake();
    }
  });
}

/* ------------------------------------------------------------------
 * Axios instance
 * ------------------------------------------------------------------ */
export const api = axios.create({ baseURL: API_URL, timeout: 90_000 });

// Wrap the adapter so *every* request participates in the slow-server indicator.
const defaultAdapter = axios.getAdapter(axios.defaults.adapter);
api.defaults.adapter = (config) => trackSlow(defaultAdapter(config));

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  config.headers['Accept-Language'] = getLang();
  return config;
});

let authFailureHandler: (() => void) | null = null;
export function onAuthFailure(fn: () => void) {
  authFailureHandler = fn;
}

let refreshing: Promise<TokenPair> | null = null;

/** Single-flight refresh: concurrent 401s wait for the same refresh call. */
export function refreshTokens(): Promise<TokenPair> {
  const rt = tokens.refresh;
  if (!rt) return Promise.reject(new Error('no refresh token'));
  if (!refreshing) {
    refreshing = trackSlow(axios.post<TokenPair>(
        `${API_URL}/auth/refresh`,
        { refresh_token: rt },
        { timeout: 90_000, headers: { 'Accept-Language': getLang() } },
      ))
      .then((res) => {
        tokens.set(res.data);
        return res.data;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError<ApiErrorBody>) => {
    const config = error.config as RetriableConfig | undefined;
    const url = config?.url ?? '';
    const isAuthCall = url.includes('/auth/login') || url.includes('/auth/refresh');
    const code = (error.response?.data as Partial<ApiErrorBody> | undefined)?.code;
    if (error.response?.status === 403 && code === 'ONBOARDING_REQUIRED' && !window.location.pathname.startsWith('/onboarding')) {
      window.location.assign('/onboarding');
    }
    if (error.response?.status === 401 && config && !config._retried && !isAuthCall && tokens.refresh) {
      config._retried = true;
      try {
        await refreshTokens();
        config.headers.Authorization = `Bearer ${tokens.access}`;
        return api(config);
      } catch {
        tokens.clear();
        authFailureHandler?.();
      }
    }
    return Promise.reject(error);
  },
);

/** User-facing message (current language) for any error thrown by the API layer. */
export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const body = err.response?.data as Partial<ApiErrorBody> | undefined;
    if (body && typeof body.detail === 'string') return body.detail;
    if (!err.response) return tr.common.networkError;
  }
  return tr.common.errorTitle;
}

export function errorCode(err: unknown): string | undefined {
  if (axios.isAxiosError(err)) return (err.response?.data as Partial<ApiErrorBody> | undefined)?.code;
  return undefined;
}
