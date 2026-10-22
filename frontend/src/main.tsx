import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import { ServerWakeBanner } from '@/components/ServerWakeBanner';
import { AuthProvider } from '@/hooks/useAuth';
import { LanguageBoundary, useLang } from '@/i18n';
import { ThemeProvider, useTheme } from '@/hooks/useTheme';
import { AppRoutes } from '@/routes/AppRoutes';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // Don't retry 4xx (permission/validation) errors, only transient failures.
      retry: (count, err) => {
        const status = axios.isAxiosError(err) ? err.response?.status : undefined;
        if (status && status >= 400 && status < 500) return false;
        return count < 2;
      },
    },
  },
});

function ThemedToaster() {
  const { isDark } = useTheme();
  const { dir } = useLang();
  return (
    <Toaster
      dir={dir}
      position="top-center"
      richColors
      closeButton
      theme={isDark ? 'dark' : 'light'}
      toastOptions={{ style: { fontFamily: 'inherit' } }}
    />
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            {/* Remounts on language change; kept inside AuthProvider so switching language keeps you logged in. */}
            <LanguageBoundary>
              <AppRoutes />
              <ServerWakeBanner />
              <ThemedToaster />
            </LanguageBoundary>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
