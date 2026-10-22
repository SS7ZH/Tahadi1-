import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link2, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { adminApi } from '@/api/endpoints';
import { Badge, Card, EmptyState, ErrorState, Input, PageHeader, Select, Skeleton } from '@/components/ui';
import { useAdminUsers, useClients } from '@/hooks/queries';
import { tr } from '@/i18n';

export function AssignPage() {
  const qc = useQueryClient();
  const clients = useClients();
  const trainers = useAdminUsers('trainer');
  const [q, setQ] = useState('');
  const [trainerFilter, setTrainerFilter] = useState('');

  const assign = useMutation({
    mutationFn: ({ clientId, trainerId }: { clientId: number; trainerId: number | null }) => adminApi.assignTrainer(clientId, trainerId),
    onSuccess: async () => {
      toast.success(tr.admin.assigned);
      await Promise.all([qc.invalidateQueries({ queryKey: ['clients'] }), qc.invalidateQueries({ queryKey: ['admin'] })]);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const list = useMemo(() => {
    const s = q.trim().toLowerCase();
    return (clients.data ?? []).filter(
      (c) =>
        (!s || c.full_name.toLowerCase().includes(s) || c.email.toLowerCase().includes(s)) &&
        (trainerFilter === '' ||
          (trainerFilter === 'none' ? c.trainer_id === null : String(c.trainer_id) === trainerFilter)),
    );
  }, [clients.data, q, trainerFilter]);

  const activeTrainers = trainers.data?.filter((t) => t.is_active) ?? [];

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title={tr.admin.assignTitle} subtitle={tr.admin.assignSubtitle} />
      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <Input aria-label={tr.common.search} placeholder={tr.common.search} value={q} onChange={(e) => setQ(e.target.value)} suffix={<Search className="h-4 w-4" />} />
        <Select aria-label={tr.client.trainer} value={trainerFilter} onChange={(e) => setTrainerFilter(e.target.value)}>
          <option value="">{tr.admin.allClients}</option>
          <option value="none">{tr.admin.noTrainer}</option>
          {trainers.data?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.full_name}
            </option>
          ))}
        </Select>
      </div>

      {clients.isLoading ? (
        <Skeleton className="h-80" />
      ) : clients.error ? (
        <ErrorState message={errorMessage(clients.error)} onRetry={() => clients.refetch()} />
      ) : !list.length ? (
        <Card>
          <EmptyState icon={<Link2 className="h-6 w-6" />} title={tr.trainer.noResults} />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <ul className="divide-y divide-line">
            {list.map((c) => (
              <li key={c.id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:px-5">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Link to={`/admin/clients/${c.id}`} className="truncate font-semibold hover:text-primary">
                      {c.full_name}
                    </Link>
                    {c.trainer_id === null && <Badge tone="bad">{tr.admin.noTrainer}</Badge>}
                  </div>
                  <p className="truncate text-xs text-muted" dir="ltr">
                    {c.email}
                  </p>
                </div>
                <Select
                  aria-label={`${tr.client.trainer} — ${c.full_name}`}
                  value={c.trainer_id ?? ''}
                  disabled={assign.isPending}
                  wrapperClassName="sm:w-60"
                  onChange={(e) => assign.mutate({ clientId: c.id, trainerId: e.target.value ? Number(e.target.value) : null })}
                >
                  <option value="">{tr.admin.noTrainer}</option>
                  {activeTrainers.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.full_name}
                    </option>
                  ))}
                </Select>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
