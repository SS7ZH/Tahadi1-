import { ArrowRight, ClipboardList, History, LayoutGrid, LineChart, MessageCircleQuestion, MessageSquare, Pencil, PlusCircle, Salad } from 'lucide-react';
import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { errorMessage } from '@/api/client';
import type { Session } from '@/api/types';
import { CommentThread } from '@/components/CommentThread';
import { NutritionPanel } from '@/components/NutritionPanel';
import { ProgramsTab } from '@/components/ProgramsTab';
import { ProgressPanel } from '@/components/ProgressPanel';
import { QuestionThread } from '@/components/QuestionThread';
import { SessionForm } from '@/components/SessionForm';
import { SessionHistory } from '@/components/SessionHistory';
import { SummaryView } from '@/components/SummaryView';
import { Badge, Button, Card, ErrorState, Skeleton, Tabs, type TabItem } from '@/components/ui';
import { useCurrentUser } from '@/hooks/useAuth';
import { useActivityFactors, useClient, useNutrition, useQuestions } from '@/hooks/queries';
import { loc, tr } from '@/i18n';
import { fmtDate, fmtNumber } from '@/lib/format';
import { ClientFormModal } from './ClientFormModal';

type Tab = 'summary' | 'progress' | 'history' | 'new' | 'nutrition' | 'program' | 'comments' | 'questions';
const TABS: Tab[] = ['summary', 'progress', 'history', 'new', 'nutrition', 'program', 'comments', 'questions'];

export function ClientPage() {
  const user = useCurrentUser();
  const clientId = Number(useParams().clientId);
  const [params, setParams] = useSearchParams();
  const tabParam = params.get('tab') as Tab | null;
  const tab: Tab = tabParam && TABS.includes(tabParam) ? tabParam : 'summary';
  const setTab = (t: Tab) => setParams(t === 'summary' ? {} : { tab: t }, { replace: true });

  const client = useClient(clientId);
  const questions = useQuestions(clientId);
  const nutrition = useNutrition(clientId);
  const factors = useActivityFactors();
  const [editing, setEditing] = useState<Session | null>(null);
  const [editProfile, setEditProfile] = useState(false);

  const back = user.role === 'admin' ? '/admin/users?role=client' : '/trainer';

  if (client.isLoading)
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-28" />
        <Skeleton className="h-12" />
        <Skeleton className="h-80" />
      </div>
    );
  if (client.error || !client.data) return <ErrorState message={errorMessage(client.error)} onRetry={() => client.refetch()} />;

  const c = client.data;
  const p = c.profile;
  const openQ = questions.data?.filter((q) => q.status === 'open').length ?? 0;
  const activity = factors.data?.find((f) => f.key === p?.activity_key);

  const items: TabItem<Tab>[] = [
    { value: 'summary', label: tr.tabs.summary, icon: <LayoutGrid className="h-4 w-4" /> },
    { value: 'progress', label: tr.tabs.progress, icon: <LineChart className="h-4 w-4" /> },
    { value: 'history', label: tr.tabs.history, icon: <History className="h-4 w-4" /> },
    { value: 'new', label: editing ? tr.tabs.editSession : tr.tabs.newSession, icon: <PlusCircle className="h-4 w-4" /> },
    { value: 'nutrition', label: tr.tabs.nutrition, icon: <Salad className="h-4 w-4" />, badge: nutrition.data?.suggestion_changed ? 1 : 0 },
    { value: 'program', label: tr.tabs.program, icon: <ClipboardList className="h-4 w-4" /> },
    { value: 'comments', label: tr.tabs.comments, icon: <MessageSquare className="h-4 w-4" /> },
    { value: 'questions', label: tr.tabs.questions, icon: <MessageCircleQuestion className="h-4 w-4" />, badge: openQ },
  ];

  return (
    <div className="flex flex-col gap-4">
      <Link to={back} className="inline-flex items-center gap-1 self-start text-sm text-muted hover:text-ink">
        <ArrowRight className="h-4 w-4 ltr:rotate-180" />
        {tr.common.back}
      </Link>

      <Card className="flex flex-wrap items-center gap-4 p-4 sm:p-5">
        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-xl font-bold text-on-primary">
          {c.full_name.charAt(0)}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-bold">{c.full_name}</h1>
            {!c.is_active && <Badge tone="bad">{tr.common.inactive}</Badge>}
            {p && <Badge tone="primary">{tr.goals[p.goal]}</Badge>}
          </div>
          <p className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-muted">
            {p && <span>{tr.sex[p.sex]}</span>}
            {c.age != null && (
              <span>
                <span className="num">{c.age}</span> {tr.common.years}
              </span>
            )}
            {p?.height_cm && (
              <span>
                <span className="num">{fmtNumber(p.height_cm)}</span> {tr.common.cm}
              </span>
            )}
            {activity && <span>{loc(activity.name_ar, activity.name_en)}</span>}
            {user.role === 'admin' && <span>{tr.client.trainer}: {c.trainer_name ?? tr.admin.noTrainer}</span>}
            {p?.birth_date && <span className="hidden sm:inline">{tr.client.birthDate}: {fmtDate(p.birth_date)}</span>}
          </p>
          {p?.notes && <p className="mt-2 flex items-start gap-1.5 text-xs text-ink/70"><ClipboardList className="mt-0.5 h-3.5 w-3.5 shrink-0" />{p.notes}</p>}
        </div>
        <Button variant="outline" size="sm" icon={<Pencil className="h-4 w-4" />} onClick={() => setEditProfile(true)}>
          {tr.common.edit}
        </Button>
      </Card>

      <Tabs
        items={items}
        value={tab}
        onChange={(t) => {
          if (t !== 'new') setEditing(null);
          setTab(t);
        }}
      />

      <div>
        {tab === 'summary' && <SummaryView clientId={clientId} audience="staff" />}
        {tab === 'progress' && <ProgressPanel clientId={clientId} />}
        {tab === 'history' && (
          <SessionHistory
            clientId={clientId}
            canEdit
            onEdit={(s) => {
              setEditing(s);
              setTab('new');
            }}
          />
        )}
        {tab === 'new' && (
          <SessionForm
            clientId={clientId}
            session={editing}
            onDone={() => {
              setEditing(null);
              setTab('history');
            }}
            onCancel={
              editing
                ? () => {
                    setEditing(null);
                    setTab('history');
                  }
                : undefined
            }
          />
        )}
        {tab === 'nutrition' && <NutritionPanel clientId={clientId} />}
        {tab === 'program' && <ProgramsTab client={c} />}
        {tab === 'comments' && <CommentThread clientId={clientId} canWrite />}
        {tab === 'questions' && <QuestionThread clientId={clientId} mode="staff" />}
      </div>

      <ClientFormModal open={editProfile} onClose={() => setEditProfile(false)} client={c} />
    </div>
  );
}
