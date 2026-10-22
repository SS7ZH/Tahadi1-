import { api } from '@/api/client';
import { getLang } from '@/i18n';

function filenameFrom(disposition: string | undefined, fallback: string): string {
  if (!disposition) return fallback;
  const star = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (star) return decodeURIComponent(star[1]);
  const plain = /filename="?([^";]+)"?/i.exec(disposition);
  return plain ? plain[1] : fallback;
}

/** Downloads a PDF from the API (Bearer auth) in the current interface language. */
export async function downloadPdf(path: string, opts: { method?: 'GET' | 'POST'; body?: unknown; params?: Record<string, unknown> } = {}) {
  const res = await api.request<Blob>({
    url: path,
    method: opts.method ?? 'GET',
    data: opts.body,
    params: { ...opts.params, lang: getLang() },
    responseType: 'blob',
    timeout: 120_000,
  });
  const name = filenameFrom(res.headers['content-disposition'] as string | undefined, 'tahadi.pdf');
  const url = URL.createObjectURL(res.data);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
