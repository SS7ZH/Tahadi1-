import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Eye, Pencil, Plus, Power, Search, Trash2, Users } from 'lucide-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { adminApi } from '@/api/endpoints';
import type { Role, User } from '@/api/types';
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, IconButton, Input, PageHeader, Skeleton, Tabs } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { useAdminUsers } from '@/hooks/queries';
import { tr } from '@/i18n';
import { fmtDate } from '@/lib/format';
import { UserFormModal } from './UserFormModal';

type RoleFilter = Role | 'all';
const roleTone: Record<Role, 'primary' | 'accent' | 'neutral'> = { admin: 'primary', trainer: 'accent', client: 'neutral' };

export function UsersPage() {
  const me = useCurrentUser();
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const roleParam = params.get('role') as Role | null;
  const role: RoleFilter = roleParam && ['admin', 'trainer', 'client'].includes(roleParam) ? roleParam : 'all';
  const [q, setQ] = useState('');
  const { data, isLoading, error, refetch } = useAdminUsers(role === 'all' ? undefined : role, q.trim());
  const [modal, setModal] = useState<{ open: boolean; user?: User | null }>({ open: false });
  const [toDelete, setToDelete] = useState<User | null>(null);

  const invalidate = () => Promise.all([qc.invalidateQueries({ queryKey: ['admin'] }), qc.invalidateQueries({ queryKey: ['clients'] })]);

  const toggle = useMutation({
    mutationFn: (u: User) => adminApi.updateUser(u.id, { is_active: !u.is_active }),
    onSuccess: async () => {
      toast.success(tr.admin.userUpdated);
      await invalidate();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const del = useMutation({
    mutationFn: (u: User) => adminApi.deleteUser(u.id),
    onSuccess: async () => {
      toast.success(tr.admin.userDeleted);
      setToDelete(null);
      await invalidate();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <div>
      <PageHeader
        title={tr.admin.users}
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => setModal({ open: true, user: null })}>
            {tr.admin.newUser}
          </Button>
        }
      />
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs<RoleFilter>
          value={role}
          onChange={(r) => setParams(r === 'all' ? {} : { role: r }, { replace: true })}
          items={[
            { value: 'all', label: tr.common.all },
            { value: 'trainer', label: tr.admin.trainers },
            { value: 'client', label: tr.admin.clients },
            { value: 'admin', label: tr.roles.admin },
          ]}
        />
        <Input
          aria-label={tr.common.search}
          placeholder={tr.common.search}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          wrapperClassName="sm:w-72"
          suffix={<Search className="h-4 w-4" />}
        />
      </div>

      {isLoading ? (
        <Skeleton className="h-80" />
      ) : error ? (
        <ErrorState message={errorMessage(error)} onRetry={() => refetch()} />
      ) : !data?.length ? (
        <Card>
          <EmptyState icon={<Users className="h-6 w-6" />} title={tr.admin.noUsers} />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <ul className="divide-y divide-line">
            {data.map((u) => (
              <li key={u.id} className="flex flex-wrap items-center gap-3 px-4 py-3 sm:flex-nowrap sm:px-5">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-surface-2 font-bold">
                  {u.full_name.charAt(0)}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate font-semibold">{u.full_name}</p>
                    <Badge tone={roleTone[u.role]}>{tr.roles[u.role]}</Badge>
                    {!u.is_active && <Badge tone="bad">{tr.common.inactive}</Badge>}
                  </div>
                  <p className="mt-0.5 truncate text-xs text-muted">
                    <span dir="ltr">{u.email}</span>
                    {u.role === 'client' && <> · {tr.client.trainer}: {u.trainer_name ?? tr.admin.noTrainer}</>}
                    <span className="hidden sm:inline"> · {fmtDate(u.created_at.slice(0, 10))}</span>
                  </p>
                </div>
                <div className="flex items-center">
                  {u.role === 'client' && (
                    <Link
                      to={`/admin/clients/${u.id}`}
                      aria-label={tr.tabs.summary}
                      title={tr.tabs.summary}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-muted transition hover:bg-surface-2 hover:text-ink"
                    >
                      <Eye className="h-4 w-4" />
                    </Link>
                  )}
                  <IconButton label={tr.common.edit} onClick={() => setModal({ open: true, user: u })}>
                    <Pencil className="h-4 w-4" />
                  </IconButton>
                  {u.id !== me.id && (
                    <>
                      <IconButton
                        label={u.is_active ? tr.admin.deactivate : tr.admin.activate}
                        onClick={() => toggle.mutate(u)}
                        className={u.is_active ? 'hover:text-warn' : 'text-good'}
                      >
                        <Power className="h-4 w-4" />
                      </IconButton>
                      <IconButton label={tr.common.delete} onClick={() => setToDelete(u)} className="hover:bg-bad/10 hover:text-bad">
                        <Trash2 className="h-4 w-4" />
                      </IconButton>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <UserFormModal
        open={modal.open}
        user={modal.user}
        defaultRole={role === 'all' ? undefined : role}
        onClose={() => setModal({ open: false })}
      />
      <ConfirmDialog
        open={!!toDelete}
        title={tr.admin.deleteUserTitle}
        text={`${toDelete?.full_name ?? ''}: ${tr.admin.deleteUserText}`}
        onConfirm={() => toDelete && del.mutate(toDelete)}
        onClose={() => setToDelete(null)}
        loading={del.isPending}
      />
    </div>
  );
}
