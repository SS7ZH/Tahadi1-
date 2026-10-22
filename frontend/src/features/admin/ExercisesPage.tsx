import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, Plus, Power, Save, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { programsApi } from '@/api/endpoints';
import { EQUIPMENT, MUSCLE_GROUPS, type Exercise } from '@/api/types';
import { Badge, Button, Card, ErrorState, IconButton, Input, Modal, PageHeader, Select, Skeleton } from '@/components/ui';
import { useExercises } from '@/hooks/queries';
import { loc, tr } from '@/i18n';

type Form = { name_ar: string; name_en: string; muscle_group: string; equipment: string; video_url: string };
const empty: Form = { name_ar: '', name_en: '', muscle_group: 'chest', equipment: '', video_url: '' };

function ExerciseModal({ open, onClose, exercise }: { open: boolean; onClose: () => void; exercise: Exercise | null }) {
  const qc = useQueryClient();
  const [f, setF] = useState<Form>(
    exercise
      ? { name_ar: exercise.name_ar, name_en: exercise.name_en, muscle_group: exercise.muscle_group, equipment: exercise.equipment ?? '', video_url: exercise.video_url ?? '' }
      : empty,
  );
  const set = (k: keyof Form, v: string) => setF((s) => ({ ...s, [k]: v }));
  const save = useMutation({
    mutationFn: () => {
      const body = { ...f, equipment: f.equipment || null, video_url: f.video_url.trim() || null };
      return exercise ? programsApi.updateExercise(exercise.id, body) : programsApi.createExercise(body);
    },
    onSuccess: async () => {
      toast.success(tr.program.exerciseSaved);
      await qc.invalidateQueries({ queryKey: ['exercises'] });
      onClose();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={exercise ? tr.common.edit : tr.program.newExercise}
      footer={
        <Button loading={save.isPending} disabled={!f.name_ar.trim() || !f.name_en.trim()} onClick={() => save.mutate()} icon={<Save className="h-4 w-4" />}>
          {tr.common.save}
        </Button>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Input label={tr.program.nameAr} value={f.name_ar} onChange={(e) => set('name_ar', e.target.value)} />
        <Input label={tr.program.nameEn} dir="ltr" value={f.name_en} onChange={(e) => set('name_en', e.target.value)} />
        <Select label={tr.program.muscle} value={f.muscle_group} onChange={(e) => set('muscle_group', e.target.value)}>
          {MUSCLE_GROUPS.map((m) => (
            <option key={m} value={m}>
              {tr.muscles[m]}
            </option>
          ))}
        </Select>
        <Select label={tr.program.equipmentLabel} value={f.equipment} onChange={(e) => set('equipment', e.target.value)}>
          <option value="">—</option>
          {EQUIPMENT.map((q) => (
            <option key={q} value={q}>
              {tr.equipment[q]}
            </option>
          ))}
        </Select>
        <Input label={tr.program.video} dir="ltr" placeholder="https://…" value={f.video_url} onChange={(e) => set('video_url', e.target.value)} wrapperClassName="sm:col-span-2" />
      </div>
    </Modal>
  );
}

export function ExercisesPage() {
  const qc = useQueryClient();
  const { data, isLoading, error, refetch } = useExercises(true);
  const [q, setQ] = useState('');
  const [muscle, setMuscle] = useState('');
  const [modal, setModal] = useState<{ open: boolean; exercise: Exercise | null }>({ open: false, exercise: null });
  const toggle = useMutation({
    mutationFn: (e: Exercise) => programsApi.updateExercise(e.id, { is_active: !e.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['exercises'] }),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const list = useMemo(() => {
    const s = q.trim().toLowerCase();
    return (data ?? []).filter((e) => (!muscle || e.muscle_group === muscle) && (!s || e.name_en.toLowerCase().includes(s) || e.name_ar.includes(q.trim())));
  }, [data, q, muscle]);

  return (
    <div>
      <PageHeader
        title={tr.program.library}
        subtitle={tr.program.librarySubtitle}
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => setModal({ open: true, exercise: null })}>
            {tr.program.newExercise}
          </Button>
        }
      />
      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <Input aria-label={tr.common.search} placeholder={tr.common.search} value={q} onChange={(e) => setQ(e.target.value)} suffix={<Search className="h-4 w-4" />} />
        <Select aria-label={tr.program.muscle} value={muscle} onChange={(e) => setMuscle(e.target.value)}>
          <option value="">{tr.program.allMuscles}</option>
          {MUSCLE_GROUPS.map((m) => (
            <option key={m} value={m}>
              {tr.muscles[m]}
            </option>
          ))}
        </Select>
      </div>
      {isLoading ? (
        <Skeleton className="h-96" />
      ) : error ? (
        <ErrorState message={errorMessage(error)} onRetry={() => refetch()} />
      ) : (
        <Card className="overflow-hidden">
          <ul className="divide-y divide-line">
            {list.map((e) => (
              <li key={e.id} className={`flex flex-wrap items-center gap-2 px-4 py-2.5 sm:px-5 ${e.is_active ? '' : 'opacity-50'}`}>
                <button type="button" className="min-w-0 flex-1 text-start" onClick={() => setModal({ open: true, exercise: e })}>
                  <span className="font-semibold">{loc(e.name_ar, e.name_en)}</span>
                  <span className="ms-2 text-xs text-muted" dir="auto">
                    {loc(e.name_en, e.name_ar)}
                  </span>
                </button>
                <Badge>{tr.muscles[e.muscle_group] ?? e.muscle_group}</Badge>
                {e.equipment && <Badge tone="accent">{tr.equipment[e.equipment] ?? e.equipment}</Badge>}
                {e.video_url && (
                  <a href={e.video_url} target="_blank" rel="noopener noreferrer" className="text-primary" aria-label={tr.program.watch}>
                    <ExternalLink className="h-4 w-4" />
                  </a>
                )}
                <IconButton label={e.is_active ? tr.admin.deactivate : tr.admin.activate} onClick={() => toggle.mutate(e)}>
                  <Power className="h-4 w-4" />
                </IconButton>
              </li>
            ))}
          </ul>
        </Card>
      )}
      {modal.open && <ExerciseModal open onClose={() => setModal({ open: false, exercise: null })} exercise={modal.exercise} />}
    </div>
  );
}
