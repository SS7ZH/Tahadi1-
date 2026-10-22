import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, History, Save } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { documentsApi } from '@/api/endpoints';
import type { TemplateKind, TemplateVersion } from '@/api/types';
import { Badge, Button, Card, CardHeader, ErrorState, PageHeader, Skeleton, Tabs, Textarea } from '@/components/ui';
import { tr, useLang } from '@/i18n';
import { fmtDateTime, todayISO } from '@/lib/format';

const SAMPLE: Record<string, string> = {
  client_name: 'سارة أحمد / Sara Ahmed',
  coach_name: 'خالد العتيبي / Khalid Alotaibi',
  plan: '3 أشهر / 3 months',
  start_date: '2026-11-01',
  end_date: '2027-01-31',
  price: '750.00 SAR',
  today: todayISO(),
};
const render = (body: string) => body.replace(/\{(\w+)\}/g, (m, k) => SAMPLE[k] ?? m);

function Editor({ kind, active, placeholders }: { kind: TemplateKind; active: TemplateVersion | undefined; placeholders: string[] }) {
  const qc = useQueryClient();
  const { lang } = useLang();
  const [bodyAr, setBodyAr] = useState(active?.body_ar ?? '');
  const [bodyEn, setBodyEn] = useState(active?.body_en ?? '');
  const [focus, setFocus] = useState<'ar' | 'en'>(lang);
  const arRef = useRef<HTMLTextAreaElement>(null);
  const enRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    setBodyAr(active?.body_ar ?? '');
    setBodyEn(active?.body_en ?? '');
  }, [active?.id, active?.body_ar, active?.body_en]);

  const dirty = bodyAr !== (active?.body_ar ?? '') || bodyEn !== (active?.body_en ?? '');
  const save = useMutation({
    mutationFn: () => documentsApi.newTemplateVersion({ kind, body_ar: bodyAr, body_en: bodyEn }),
    onSuccess: async (v) => {
      toast.success(tr.templatesAdmin.savedVersion(v.version));
      await qc.invalidateQueries({ queryKey: ['admin', 'templates', kind] });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const insert = (ph: string) => {
    const el = focus === 'ar' ? arRef.current : enRef.current;
    const setter = focus === 'ar' ? setBodyAr : setBodyEn;
    const value = focus === 'ar' ? bodyAr : bodyEn;
    const pos = el?.selectionStart ?? value.length;
    setter(value.slice(0, pos) + `{${ph}}` + value.slice(pos));
    requestAnimationFrame(() => el?.focus());
  };
  const preview = useMemo(() => render(focus === 'ar' ? bodyAr : bodyEn), [focus, bodyAr, bodyEn]);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="flex flex-col gap-3 p-4">
        <div>
          <p className="mb-2 text-xs font-semibold text-muted">{tr.templatesAdmin.placeholders}</p>
          <div className="flex flex-wrap gap-1.5">
            {placeholders.map((p) => (
              <button key={p} type="button" onClick={() => insert(p)} className="rounded-lg bg-surface-2 px-2 py-1 font-mono text-xs hover:bg-primary/10 hover:text-primary" dir="ltr">
                {`{${p}}`}
              </button>
            ))}
          </div>
        </div>
        <Textarea ref={arRef} label={tr.templatesAdmin.bodyAr} dir="rtl" rows={12} value={bodyAr} onFocus={() => setFocus('ar')} onChange={(e) => setBodyAr(e.target.value)} />
        <Textarea ref={enRef} label={tr.templatesAdmin.bodyEn} dir="ltr" rows={12} value={bodyEn} onFocus={() => setFocus('en')} onChange={(e) => setBodyEn(e.target.value)} />
        <Button icon={<Save className="h-4 w-4" />} disabled={!dirty || bodyAr.trim().length < 20 || bodyEn.trim().length < 20} loading={save.isPending} onClick={() => save.mutate()} className="self-start">
          {tr.templatesAdmin.newVersion}
        </Button>
      </Card>
      <Card className="flex flex-col">
        <CardHeader title={`${tr.templatesAdmin.preview} (${focus === 'ar' ? 'العربية' : 'English'})`} subtitle={tr.templatesAdmin.previewSample} />
        <pre dir={focus === 'ar' ? 'rtl' : 'ltr'} className="max-h-[70vh] flex-1 overflow-auto whitespace-pre-wrap p-4 font-sans text-sm leading-relaxed">
          {preview}
        </pre>
      </Card>
    </div>
  );
}

export function TemplatesPage() {
  const [kind, setKind] = useState<TemplateKind>('contract');
  const q = useQuery({ queryKey: ['admin', 'templates', kind], queryFn: () => documentsApi.templates(kind) });
  const versions = q.data?.versions ?? [];
  const active = versions.find((v) => v.is_active);
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={tr.templatesAdmin.title} />
      <div className="flex items-start gap-2 rounded-2xl border border-warn/40 bg-warn/10 p-3 text-sm">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warn" />
        {tr.templatesAdmin.legalNote}
      </div>
      <Tabs<TemplateKind> value={kind} onChange={setKind} items={[{ value: 'contract', label: tr.docKinds.contract }, { value: 'disclaimer', label: tr.docKinds.disclaimer }]} />
      {q.isLoading ? (
        <Skeleton className="h-96" />
      ) : q.error ? (
        <ErrorState message={errorMessage(q.error)} onRetry={() => q.refetch()} />
      ) : (
        <>
          <Editor key={`${kind}-${active?.id}`} kind={kind} active={active} placeholders={q.data?.placeholders ?? []} />
          <Card>
            <CardHeader title={tr.templatesAdmin.versions} icon={<History className="h-5 w-5" />} />
            <ul className="divide-y divide-line">
              {versions.map((v) => (
                <li key={v.id} className="flex flex-wrap items-center gap-2 px-4 py-2.5 text-sm sm:px-5">
                  <b>{tr.documents.version(v.version)}</b>
                  {v.is_active && <Badge tone="good">{tr.templatesAdmin.active}</Badge>}
                  <span className="text-muted">
                    {fmtDateTime(v.created_at)}
                    {v.created_by_name ? ` · ${v.created_by_name}` : ''}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}
