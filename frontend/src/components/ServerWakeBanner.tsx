import { Loader2 } from 'lucide-react';
import { useSyncExternalStore } from 'react';
import { serverWake } from '@/api/client';
import { tr } from '@/i18n';

/** Shown when any request takes longer than 3 seconds (Render free plan cold start). */
export function ServerWakeBanner() {
  const waking = useSyncExternalStore(serverWake.subscribe, () => serverWake.isWaking);
  if (!waking) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-x-0 top-0 z-[60] flex justify-center px-4 pt-[max(env(safe-area-inset-top),0.75rem)]"
    >
      <div className="flex max-w-md items-center gap-3 rounded-2xl border border-primary/30 bg-surface px-4 py-3 shadow-xl">
        <Loader2 className="h-5 w-5 shrink-0 animate-spin text-primary" />
        <div>
          <p className="text-sm font-bold">{tr.server.waking}</p>
          <p className="text-xs text-muted">{tr.server.wakingHint}</p>
        </div>
      </div>
    </div>
  );
}
