import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, Save } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { siteApi } from '@/api/endpoints';
import type { HomeContent, HomeFeature } from '@/api/types';
import { Button, Card, CardHeader, ErrorState, Input, PageHeader, Skeleton, Textarea } from '@/components/ui';
import { usePublicSite } from '@/hooks/queries';
import { loc, tr } from '@/i18n';

/** Two side-by-side fields (Arabic RTL / English LTR) for one bilingual value. */
function Bilingual({
  label,
  ar,
  en,
  onAr,
  onEn,
  max,
  multiline,
}: {
  label: string;
  ar: string;
  en: string;
  onAr: (v: string) => void;
  onEn: (v: string) => void;
  max: number;
  multiline?: boolean;
}) {
  const Comp = multiline ? Textarea : Input;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Comp label={`${label} · ${tr.siteAdmin.arabic}`} dir="rtl" maxLength={max} value={ar} onChange={(e) => onAr(e.target.value)} />
      <Comp label={`${label} · ${tr.siteAdmin.english}`} dir="ltr" maxLength={max} value={en} onChange={(e) => onEn(e.target.value)} />
    </div>
  );
}

const filled = (c: HomeContent) =>
  [c.hero_title_ar, c.hero_title_en, c.hero_text_ar, c.hero_text_en].every((s) => s.trim()) &&
  c.features.every((f) => [f.title_ar, f.title_en, f.text_ar, f.text_en].every((s) => s.trim()));

export function SiteContentPage() {
  const qc = useQueryClient();
  const site = usePublicSite();
  const [form, setForm] = useState<HomeContent | null>(null);
  useEffect(() => {
    if (site.data) setForm(site.data.home);
  }, [site.data]);

  const save = useMutation({
    mutationFn: (body: HomeContent) => siteApi.updateHome(body),
    onSuccess: (res) => {
      qc.setQueryData(['public', 'site'], res);
      toast.success(tr.siteAdmin.saved);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  if (site.isError) return <ErrorState message={errorMessage(site.error)} onRetry={() => site.refetch()} />;
  if (!form) return <Skeleton className="h-96" />;

  const set = (patch: Partial<HomeContent>) => setForm({ ...form, ...patch });
  const setFeature = (i: number, patch: Partial<HomeFeature>) =>
    set({ features: form.features.map((f, j) => (j === i ? { ...f, ...patch } : f)) });
  const setContact = (patch: Partial<HomeContent['contact']>) => set({ contact: { ...form.contact, ...patch } });
  const dirty = JSON.stringify(form) !== JSON.stringify(site.data?.home);

  return (
    <div className="flex flex-col gap-4 pb-24">
      <PageHeader
        title={tr.siteAdmin.title}
        actions={
          <Link to="/" target="_blank">
            <Button variant="outline" size="sm" icon={<ExternalLink className="h-4 w-4" />}>
              {tr.siteAdmin.preview}
            </Button>
          </Link>
        }
      />

      <Card>
        <CardHeader title={tr.siteAdmin.hero} />
        <div className="flex flex-col gap-3 p-4">
          <Bilingual label={tr.siteAdmin.heroTitle} max={120} ar={form.hero_title_ar} en={form.hero_title_en} onAr={(v) => set({ hero_title_ar: v })} onEn={(v) => set({ hero_title_en: v })} />
          <Bilingual label={tr.siteAdmin.heroText} max={400} multiline ar={form.hero_text_ar} en={form.hero_text_en} onAr={(v) => set({ hero_text_ar: v })} onEn={(v) => set({ hero_text_en: v })} />
        </div>
      </Card>

      <Card>
        <CardHeader title={tr.siteAdmin.features} />
        <div className="flex flex-col divide-y divide-line">
          {form.features.map((f, i) => (
            <div key={f.key} className="flex flex-col gap-3 p-4">
              <p className="text-sm font-bold text-primary">
                <span className="num">{i + 1}.</span> {loc(site.data!.home.features[i].title_ar, site.data!.home.features[i].title_en)}
              </p>
              <Bilingual label={tr.siteAdmin.heroTitle} max={80} ar={f.title_ar} en={f.title_en} onAr={(v) => setFeature(i, { title_ar: v })} onEn={(v) => setFeature(i, { title_en: v })} />
              <Bilingual label={tr.siteAdmin.heroText} max={300} multiline ar={f.text_ar} en={f.text_en} onAr={(v) => setFeature(i, { text_ar: v })} onEn={(v) => setFeature(i, { text_en: v })} />
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader title={tr.siteAdmin.contact} />
        <div className="grid gap-3 p-4 sm:grid-cols-3">
          <Input label={tr.landing.phone} dir="ltr" type="tel" inputMode="tel" maxLength={30} placeholder="+966 5x xxx xxxx" value={form.contact.phone} onChange={(e) => setContact({ phone: e.target.value })} />
          <Input label={tr.landing.whatsapp} dir="ltr" type="tel" inputMode="tel" maxLength={30} placeholder="+966 5x xxx xxxx" value={form.contact.whatsapp} onChange={(e) => setContact({ whatsapp: e.target.value })} />
          <Input label={tr.landing.email} dir="ltr" type="email" maxLength={120} value={form.contact.email} onChange={(e) => setContact({ email: e.target.value })} />
        </div>
      </Card>

      <div className="sticky bottom-20 z-10 flex justify-end md:bottom-4">
        <Button icon={<Save className="h-4 w-4" />} disabled={!dirty || !filled(form)} loading={save.isPending} onClick={() => save.mutate(form)} className="shadow-lg">
          {tr.common.save}
        </Button>
      </div>
    </div>
  );
}
