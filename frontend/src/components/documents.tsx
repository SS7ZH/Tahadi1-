import clsx from 'clsx';
import { FileText, Loader2, Paperclip, ShieldAlert, Trash2, Upload } from 'lucide-react';
import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { documentsApi } from '@/api/endpoints';
import { CHRONIC_CONDITIONS, type HealthDeclarationInfo, type HealthInput, type MedicalFileInfo, type SignedDocumentInfo } from '@/api/types';
import { tr } from '@/i18n';
import { fmtDate, fmtDateTime } from '@/lib/format';
import { Badge, Button, IconButton, Modal, Textarea } from './ui';

export const emptyHealth = (): HealthInput => ({ has_chronic: false, conditions: [], details: '', medications: '', injuries: '', file_ids: [] });

const kb = (n: number) => (n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(n / 1024)} KB`);

/** Opens a medical file through a fresh 5-minute signed link (permission is checked by the API). */
export function FileLink({ file, className }: { file: MedicalFileInfo; className?: string }) {
  const [busy, setBusy] = useState(false);
  const open = async () => {
    // open the tab synchronously (popup blockers), then point it at the signed URL
    const w = window.open('', '_blank');
    setBusy(true);
    try {
      const { url } = await documentsApi.fileUrl(file.id);
      if (w) {
        w.opener = null;
        w.location.href = url;
      } else window.location.href = url;
    } catch (e) {
      w?.close();
      toast.error(errorMessage(e) || tr.documents.fileOpenFailed);
    } finally {
      setBusy(false);
    }
  };
  return (
    <button type="button" onClick={open} title={tr.documents.linkNote} className={clsx('inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline', className)}>
      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Paperclip className="h-4 w-4" />}
      <span className="max-w-[14rem] truncate" dir="auto">
        {file.original_name}
      </span>
      <span className="text-xs font-normal text-muted">({kb(file.size_bytes)})</span>
    </button>
  );
}

export function ChronicBadge({ className }: { className?: string }) {
  return (
    <Badge tone="bad" className={className}>
      <ShieldAlert className="h-3.5 w-3.5" />
      {tr.documents.chronic}
    </Badge>
  );
}

/** Read-only declaration (coach / profile / history). */
export function DeclarationView({ d }: { d: HealthDeclarationInfo }) {
  return (
    <div className="flex flex-col gap-2 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        {d.has_chronic ? <ChronicBadge /> : <Badge tone="good">{tr.documents.noChronic}</Badge>}
        {d.conditions.map((c) => (
          <Badge key={c}>{tr.conditions[c] ?? c}</Badge>
        ))}
        <span className="text-xs text-muted">{fmtDateTime(d.created_at)}</span>
        {d.reviewed_at && <Badge tone="accent">{tr.documents.reviewed}</Badge>}
      </div>
      {d.details && <p className="whitespace-pre-line">{d.details}</p>}
      {d.medications && (
        <p>
          <b>{tr.onboarding.medications}:</b> {d.medications}
        </p>
      )}
      {d.injuries && (
        <p>
          <b>{tr.onboarding.injuries}:</b> {d.injuries}
        </p>
      )}
      {d.files.length > 0 && (
        <div className="flex flex-col gap-1">
          {d.files.map((f) => (
            <FileLink key={f.id} file={f} />
          ))}
        </div>
      )}
    </div>
  );
}

/** Health declaration form with optional uploads (used by the wizard and by later updates). */
export function HealthForm({
  value,
  onChange,
  files,
  onUpload,
  onRemoveFile,
}: {
  value: HealthInput;
  onChange: (v: HealthInput) => void;
  files: MedicalFileInfo[];
  onUpload: (f: File) => Promise<void>;
  onRemoveFile?: (id: number) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const set = (p: Partial<HealthInput>) => onChange({ ...value, ...p });
  const toggle = (c: string) =>
    set({ conditions: value.conditions.includes(c) ? value.conditions.filter((x) => x !== c) : [...value.conditions, c] });

  return (
    <div className="flex flex-col gap-4">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-semibold">{tr.onboarding.chronicQ}</legend>
        <div className="grid grid-cols-2 gap-2" role="radiogroup">
          {[true, false].map((yes) => (
            <button
              key={String(yes)}
              type="button"
              role="radio"
              aria-checked={value.has_chronic === yes}
              onClick={() => set({ has_chronic: yes, conditions: yes ? value.conditions : [] })}
              className={clsx(
                'rounded-xl border px-3 py-2.5 text-sm font-semibold transition',
                value.has_chronic === yes ? 'border-primary bg-primary/10 text-primary' : 'border-line hover:bg-surface-2',
              )}
            >
              {yes ? tr.common.yes : tr.common.no}
            </button>
          ))}
        </div>
      </fieldset>

      {value.has_chronic && (
        <>
          <fieldset>
            <legend className="mb-2 text-sm font-medium">{tr.onboarding.conditionsLabel}</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {CHRONIC_CONDITIONS.map((c) => (
                <label key={c} className={clsx('flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm', value.conditions.includes(c) ? 'border-primary bg-primary/5' : 'border-line')}>
                  <input type="checkbox" checked={value.conditions.includes(c)} onChange={() => toggle(c)} className="h-4 w-4 accent-[rgb(var(--c-primary))]" />
                  {tr.conditions[c]}
                </label>
              ))}
            </div>
          </fieldset>
          <Textarea label={tr.onboarding.details} rows={3} value={value.details ?? ''} onChange={(e) => set({ details: e.target.value })} maxLength={3000} />
        </>
      )}
      <Textarea label={tr.onboarding.medications} rows={2} value={value.medications ?? ''} onChange={(e) => set({ medications: e.target.value })} maxLength={2000} />
      <Textarea label={tr.onboarding.injuries} rows={2} value={value.injuries ?? ''} onChange={(e) => set({ injuries: e.target.value })} maxLength={2000} />

      <div>
        <p className="text-sm font-medium">{tr.onboarding.files}</p>
        <p className="mb-2 text-xs text-muted">{tr.onboarding.filesHint}</p>
        <ul className="mb-2 flex flex-col gap-1.5">
          {files.map((f) => (
            <li key={f.id} className="flex items-center gap-2 rounded-xl bg-surface-2 px-3 py-2 text-sm">
              <FileText className="h-4 w-4 text-primary" />
              <span className="flex-1 truncate" dir="auto">
                {f.original_name}
              </span>
              <span className="text-xs text-muted">{kb(f.size_bytes)}</span>
              {onRemoveFile && (
                <IconButton label={tr.onboarding.removeFile} onClick={() => onRemoveFile(f.id)} className="h-8 w-8 hover:text-bad">
                  <Trash2 className="h-4 w-4" />
                </IconButton>
              )}
            </li>
          ))}
        </ul>
        <input
          ref={input}
          type="file"
          accept="application/pdf,image/jpeg,image/png,.pdf,.jpg,.jpeg,.png"
          className="hidden"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            e.target.value = '';
            if (!file) return;
            if (file.size > 10 * 1024 * 1024) {
              toast.error(tr.onboarding.filesHint);
              return;
            }
            setUploading(true);
            try {
              await onUpload(file);
            } finally {
              setUploading(false);
            }
          }}
        />
        <Button variant="outline" size="sm" icon={<Upload className="h-4 w-4" />} loading={uploading} disabled={files.length >= 3} onClick={() => input.current?.click()}>
          {uploading ? tr.onboarding.uploading : tr.onboarding.upload}
        </Button>
      </div>
      <p className="text-xs text-muted">{tr.onboarding.privacy}</p>
    </div>
  );
}

export function SignedDocModal({ doc, onClose }: { doc: SignedDocumentInfo | null; onClose: () => void }) {
  return (
    <Modal open={!!doc} onClose={onClose} title={doc ? `${tr.docKinds[doc.kind]} · ${tr.documents.version(doc.template_version)}` : ''} size="lg">
      {doc && (
        <div className="flex flex-col gap-3">
          <pre dir={doc.language === 'ar' ? 'rtl' : 'ltr'} className="max-h-[55vh] overflow-auto whitespace-pre-wrap rounded-xl bg-surface-2 p-4 font-sans text-sm leading-relaxed">
            {doc.rendered_text}
          </pre>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-xs text-muted">{tr.documents.signedBy}</dt>
              <dd className="font-semibold" dir="auto">
                {doc.typed_name}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted">{tr.documents.signedAt}</dt>
              <dd className="font-semibold">{fmtDateTime(doc.signed_at)}</dd>
            </div>
          </dl>
        </div>
      )}
    </Modal>
  );
}

export function SignedDocList({ docs, onOpen }: { docs: SignedDocumentInfo[]; onOpen: (d: SignedDocumentInfo) => void }) {
  if (!docs.length) return <p className="p-4 text-sm text-muted">{tr.documents.noDocs}</p>;
  return (
    <ul className="divide-y divide-line">
      {docs.map((d) => (
        <li key={d.id} className="flex flex-wrap items-center gap-2 px-4 py-3 sm:px-5">
          <FileText className="h-4 w-4 text-primary" />
          <span className="font-semibold">{tr.docKinds[d.kind]}</span>
          <Badge>{tr.documents.version(d.template_version)}</Badge>
          {d.details?.plan && d.kind === 'contract' && (
            <span className="text-xs text-muted">
              {d.details.plan} · {fmtDate(d.details.start_date)} – {fmtDate(d.details.end_date)}
            </span>
          )}
          <span className="ms-auto text-xs text-muted">{fmtDateTime(d.signed_at)}</span>
          <Button size="sm" variant="ghost" onClick={() => onOpen(d)}>
            {tr.documents.view}
          </Button>
        </li>
      ))}
    </ul>
  );
}
