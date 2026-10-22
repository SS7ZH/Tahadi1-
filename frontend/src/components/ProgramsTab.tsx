import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Archive, ArrowRight, BookmarkPlus, ClipboardList, Copy, Eye, FileDown, Pencil, Play, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { programsApi } from '@/api/endpoints';
import type { Program, ProgramInput, ProgramSummary, User } from '@/api/types';
import { useClients, useProgram, usePrograms, useProgramTemplates } from '@/hooks/queries';
import { tr } from '@/i18n';
import { downloadPdf } from '@/lib/download';
import { fmtDate, fmtDateTime } from '@/lib/format';
import { ChronicBadge } from './documents';
import { ProgramBuilder } from './ProgramBuilder';
import { ProgramView } from './ProgramView';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, Input, Modal, Select, Skeleton } from './ui';

type Mode = { kind: 'list' } | { kind: 'new' } | { kind: 'edit'; id: number } | { kind: 'view'; id: number };

function useInvalidatePrograms(clientId: number) {
  const qc = useQueryClient();
  return () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: ['client', clientId] }),
      qc.invalidateQueries({ queryKey: ['program'] }),
      qc.invalidateQueries({ queryKey: ['program-templates'] }),
    ]);
}

const statusTone = { active: 'good', draft: 'warn', archived: 'neutral' } as const;

function ProgramRow({ p, onView, onEdit }: { p: ProgramSummary; onView: () => void; onEdit: () => void }) {
  const [downloading, setDownloading] = useState(false);
  const handleExport = async () => {
    setDownloading(true);
    try {
      await downloadPdf(`/pdf/program/${p.id}`);
      toast.success(tr.pdf.exported);
    } catch (err) {
      toast.error(errorMessage(err) || tr.pdf.exportFailed);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <li className="flex flex-wrap items-center gap-3 px-4 py-3 sm:px-5">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">{p.title}</span>
          <Badge tone={statusTone[p.status]}>{tr.programStatus[p.status]}</Badge>
        </div>
        <p className="mt-0.5 text-xs text-muted">
          {p.start_date ? fmtDate(p.start_date) : tr.program.noStart} · {tr.program.weeks}: <span className="num">{p.weeks}</span> ·{' '}
          {tr.program.days}: <span className="num">{p.days_count}</span> · {fmtDateTime(p.updated_at)}
        </p>
      </div>
      <Button size="sm" variant="ghost" icon={<FileDown className="h-4 w-4" />} loading={downloading} onClick={handleExport} title={tr.pdf.exportPdf}>
        {tr.pdf.exportPdf}
      </Button>
      <Button size="sm" variant="ghost" icon={<Eye className="h-4 w-4" />} onClick={onView}>
        {tr.program.view}
      </Button>
      <Button size="sm" variant="outline" icon={<Pencil className="h-4 w-4" />} onClick={onEdit}>
        {tr.program.edit}
      </Button>
    </li>
  );
}

function EditorActions({ program, client, onDone, onDeleted }: { program: Program; client: User; onDone: (id?: number) => void; onDeleted: () => void }) {
  const invalidate = useInvalidatePrograms(client.id);
  const clients = useClients();
  const [modal, setModal] = useState<'template' | 'copy' | 'delete' | null>(null);
  const [templateName, setTemplateName] = useState(program.title);
  const [target, setTarget] = useState('');

  const run = (fn: () => Promise<unknown>, msg: string, after?: (r: unknown) => void) => ({
    mutationFn: fn,
    onSuccess: async (r: unknown) => {
      toast.success(msg);
      setModal(null);
      await invalidate();
      after?.(r);
    },
    onError: (e: unknown) => toast.error(errorMessage(e)),
  });
  const activate = useMutation(run(() => programsApi.activate(program.id), tr.program.activated));
  const archive = useMutation(run(() => programsApi.archive(program.id), tr.program.archived));
  const asTemplate = useMutation(run(() => programsApi.duplicate(program.id, { as_template: true, title: templateName }), tr.program.templateSaved));
  const copy = useMutation(run(() => programsApi.duplicate(program.id, { client_id: Number(target) }), tr.program.duplicated));
  const remove = useMutation(run(() => programsApi.remove(program.id), tr.program.deleted, onDeleted));
  const others = (clients.data ?? []).filter((c) => c.id !== client.id);

  return (
    <>
      {program.status !== 'active' && (
        <Button variant="secondary" icon={<Play className="h-4 w-4" />} loading={activate.isPending} onClick={() => activate.mutate()} title={tr.program.activateHint}>
          {tr.program.activate}
        </Button>
      )}
      {program.status === 'active' && (
        <Button variant="secondary" icon={<Archive className="h-4 w-4" />} loading={archive.isPending} onClick={() => archive.mutate()}>
          {tr.program.archive}
        </Button>
      )}
      <Button variant="ghost" icon={<BookmarkPlus className="h-4 w-4" />} onClick={() => setModal('template')}>
        {tr.program.saveTemplate}
      </Button>
      <Button variant="ghost" icon={<Copy className="h-4 w-4" />} onClick={() => setModal('copy')} disabled={!others.length}>
        {tr.program.duplicate}
      </Button>
      {program.status === 'draft' && (
        <Button variant="ghost" icon={<Trash2 className="h-4 w-4" />} onClick={() => setModal('delete')} className="text-bad hover:bg-bad/10 hover:text-bad">
          {tr.common.delete}
        </Button>
      )}
      <Button
        variant="ghost"
        icon={<FileDown className="h-4 w-4" />}
        onClick={async () => {
          try {
            await downloadPdf(`/pdf/program/${program.id}`);
            toast.success(tr.pdf.exported);
          } catch (e) {
            toast.error(errorMessage(e) || tr.pdf.exportFailed);
          }
        }}
      >
        {tr.pdf.exportPdf}
      </Button>
      <Button variant="ghost" icon={<Eye className="h-4 w-4" />} onClick={() => onDone(program.id)}>
        {tr.program.view}
      </Button>

      <Modal
        open={modal === 'template'}
        onClose={() => setModal(null)}
        title={tr.program.saveTemplate}
        size="sm"
        footer={
          <Button loading={asTemplate.isPending} disabled={!templateName.trim()} onClick={() => asTemplate.mutate()}>
            {tr.common.save}
          </Button>
        }
      >
        <Input label={tr.program.templateName} value={templateName} onChange={(e) => setTemplateName(e.target.value)} />
      </Modal>
      <Modal
        open={modal === 'copy'}
        onClose={() => setModal(null)}
        title={tr.program.duplicate}
        size="sm"
        footer={
          <Button loading={copy.isPending} disabled={!target} onClick={() => copy.mutate()}>
            {tr.program.duplicate}
          </Button>
        }
      >
        <Select label={tr.program.duplicateTo} value={target} onChange={(e) => setTarget(e.target.value)}>
          <option value="">{tr.form.choose}</option>
          {others.map((c) => (
            <option key={c.id} value={c.id}>
              {c.full_name}
            </option>
          ))}
        </Select>
      </Modal>
      <ConfirmDialog
        open={modal === 'delete'}
        title={tr.program.deleteTitle}
        text={tr.program.deleteText}
        onConfirm={() => remove.mutate()}
        onClose={() => setModal(null)}
        loading={remove.isPending}
      />
    </>
  );
}

function ProgramEditor({ id, client, maxHr, setMode }: { id: number; client: User; maxHr: number | null; setMode: (m: Mode) => void }) {
  const q = useProgram(id);
  const invalidate = useInvalidatePrograms(client.id);
  const save = useMutation({
    mutationFn: (input: ProgramInput) => programsApi.update(id, input),
    onSuccess: async () => {
      toast.success(tr.program.saved);
      await invalidate();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.error || !q.data) return <ErrorState message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  return (
    <ProgramBuilder
      key={`${q.data.id}-${q.data.status}`}
      initial={q.data}
      maxHr={maxHr}
      saving={save.isPending}
      onSave={(input) => save.mutate(input)}
      actions={<EditorActions program={q.data} client={client} onDone={(pid) => setMode({ kind: 'view', id: pid ?? id })} onDeleted={() => setMode({ kind: 'list' })} />}
    />
  );
}

export function ProgramsTab({ client, hasChronic }: { client: User; hasChronic?: boolean }) {
  const [mode, setMode] = useState<Mode>({ kind: 'list' });
  const programs = usePrograms(client.id);
  const templates = useProgramTemplates(mode.kind === 'list');
  const viewed = useProgram(mode.kind === 'view' ? mode.id : null);
  const invalidate = useInvalidatePrograms(client.id);
  const [templateId, setTemplateId] = useState('');
  const maxHr = client.age != null ? 220 - client.age : null;

  const create = useMutation({
    mutationFn: (input: ProgramInput) => programsApi.create(client.id, input),
    onSuccess: async (p) => {
      toast.success(tr.program.saved);
      await invalidate();
      setMode({ kind: 'edit', id: p.id });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const fromTemplate = useMutation({
    mutationFn: () => programsApi.duplicate(Number(templateId), { client_id: client.id }),
    onSuccess: async (p) => {
      toast.success(tr.program.duplicated);
      setTemplateId('');
      await invalidate();
      setMode({ kind: 'edit', id: p.id });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const chronic = hasChronic ? (
    <div className="flex items-center gap-2 rounded-xl border border-bad/30 bg-bad/5 px-3 py-2 text-sm">
      <ChronicBadge />
      <span className="text-muted">{tr.documents.chronicProgramHint}</span>
    </div>
  ) : null;

  const back = (
    <Button variant="ghost" size="sm" icon={<ArrowRight className="h-4 w-4 ltr:rotate-180" />} onClick={() => setMode({ kind: 'list' })} className="self-start">
      {tr.program.back}
    </Button>
  );

  if (mode.kind === 'new')
    return (
      <div className="flex flex-col gap-3">
        {back}
        {chronic}
        <ProgramBuilder maxHr={maxHr} saving={create.isPending} onSave={(input) => create.mutate(input)} />
      </div>
    );
  if (mode.kind === 'edit')
    return (
      <div className="flex flex-col gap-3">
        {back}
        {chronic}
        <ProgramEditor id={mode.id} client={client} maxHr={maxHr} setMode={setMode} />
      </div>
    );
  if (mode.kind === 'view')
    return (
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          {back}
          <Button size="sm" variant="outline" icon={<Pencil className="h-4 w-4" />} onClick={() => setMode({ kind: 'edit', id: mode.id })}>
            {tr.program.edit}
          </Button>
          {viewed.data && (
            <Button
              size="sm"
              variant="outline"
              icon={<FileDown className="h-4 w-4" />}
              onClick={async () => {
                try {
                  await downloadPdf(`/pdf/program/${mode.id}`);
                  toast.success(tr.pdf.exported);
                } catch (e) {
                  toast.error(errorMessage(e) || tr.pdf.exportFailed);
                }
              }}
            >
              {tr.pdf.exportPdf}
            </Button>
          )}
        </div>
        {viewed.isLoading ? <Skeleton className="h-96" /> : viewed.data ? <ProgramView program={viewed.data} /> : <ErrorState message={errorMessage(viewed.error)} />}
      </div>
    );

  const list = programs.data ?? [];
  const order = { active: 0, draft: 1, archived: 2 };
  const sorted = [...list].sort((a, b) => order[a.status] - order[b.status]);
  return (
    <div className="flex flex-col gap-4">
      {chronic}
      <Card className="flex flex-wrap items-end gap-3 p-4">
        <Button icon={<Plus className="h-4 w-4" />} onClick={() => setMode({ kind: 'new' })}>
          {tr.program.newProgram}
        </Button>
        <div className="flex flex-1 flex-wrap items-end gap-2">
          <Select label={tr.program.fromTemplate} value={templateId} onChange={(e) => setTemplateId(e.target.value)} wrapperClassName="min-w-[12rem] flex-1 sm:flex-none">
            <option value="">{templates.data?.length ? tr.program.chooseTemplate : tr.program.noTemplates}</option>
            {templates.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
                {t.created_by_name ? ` (${tr.program.by} ${t.created_by_name})` : ''}
              </option>
            ))}
          </Select>
          <Button variant="outline" disabled={!templateId} loading={fromTemplate.isPending} onClick={() => fromTemplate.mutate()}>
            {tr.common.create}
          </Button>
        </div>
      </Card>
      {programs.isLoading ? (
        <Skeleton className="h-40" />
      ) : programs.error ? (
        <ErrorState message={errorMessage(programs.error)} onRetry={() => programs.refetch()} />
      ) : !sorted.length ? (
        <Card>
          <EmptyState icon={<ClipboardList className="h-6 w-6" />} title={tr.program.empty} description={tr.program.emptyCoach} />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <ul className="divide-y divide-line">
            {sorted.map((p) => (
              <ProgramRow key={p.id} p={p} onView={() => setMode({ kind: 'view', id: p.id })} onEdit={() => setMode({ kind: 'edit', id: p.id })} />
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
