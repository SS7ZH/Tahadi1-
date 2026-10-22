import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  adminApi,
  clientsApi,
  documentsApi,
  nutritionApi,
  onboardingApi,
  programsApi,
  questionsApi,
  referenceApi,
  sessionsApi,
  siteApi,
} from '@/api/endpoints';
import type { QuestionStatus, Role } from '@/api/types';

export const qk = {
  definitions: ['definitions'] as const,
  activityFactors: ['activity-factors'] as const,
  clients: (params?: object) => ['clients', params ?? {}] as const,
  client: (id: number) => ['client', id] as const,
  summary: (id: number) => ['client', id, 'summary'] as const,
  progress: (id: number) => ['client', id, 'progress'] as const,
  sessions: (id: number) => ['client', id, 'sessions'] as const,
  session: (id: number) => ['session', id] as const,
  comments: (id: number) => ['client', id, 'comments'] as const,
  questions: (id: number) => ['client', id, 'questions'] as const,
  inbox: (status: string) => ['inbox', status] as const,
  adminStats: ['admin', 'stats'] as const,
  adminUsers: (role?: string, q?: string) => ['admin', 'users', role ?? 'all', q ?? ''] as const,
  adminDefinitions: ['admin', 'definitions'] as const,
  adminFactors: ['admin', 'factors'] as const,
  nutrition: (id: number) => ['client', id, 'nutrition'] as const,
  nutritionHistory: (id: number) => ['client', id, 'nutrition', 'history'] as const,
  nutritionSettings: ['nutrition-settings'] as const,
  programs: (id: number) => ['client', id, 'programs'] as const,
  currentProgram: (id: number) => ['client', id, 'program', 'current'] as const,
  program: (id: number) => ['program', id] as const,
  templates: ['program-templates'] as const,
  exercises: (all = false) => ['exercises', all] as const,
  onboarding: ['onboarding'] as const,
  subscriptions: (id: number) => ['client', id, 'subscriptions'] as const,
  health: (id: number) => ['client', id, 'health'] as const,
  documents: (id: number) => ['client', id, 'documents'] as const,
};

export const useDefinitions = () =>
  useQuery({ queryKey: qk.definitions, queryFn: referenceApi.definitions, staleTime: 10 * 60_000 });

export const useActivityFactors = () =>
  useQuery({ queryKey: qk.activityFactors, queryFn: referenceApi.activityFactors, staleTime: 10 * 60_000 });

export const useClients = (params?: { q?: string; trainer_id?: number }) =>
  useQuery({ queryKey: qk.clients(params), queryFn: () => clientsApi.list(params) });

export const useClient = (id: number) => useQuery({ queryKey: qk.client(id), queryFn: () => clientsApi.get(id) });

export const useSummary = (id: number, enabled = true) =>
  useQuery({ queryKey: qk.summary(id), queryFn: () => clientsApi.summary(id), enabled });

export const useProgress = (id: number) =>
  useQuery({ queryKey: qk.progress(id), queryFn: () => clientsApi.progress(id) });

export const useSessions = (id: number) =>
  useQuery({ queryKey: qk.sessions(id), queryFn: () => clientsApi.sessions(id) });

export const useSessionDetail = (id: number, enabled = true) =>
  useQuery({ queryKey: qk.session(id), queryFn: () => sessionsApi.get(id), enabled });

export const useComments = (id: number) =>
  useQuery({ queryKey: qk.comments(id), queryFn: () => clientsApi.comments(id) });

export const useQuestions = (id: number) =>
  useQuery({ queryKey: qk.questions(id), queryFn: () => clientsApi.questions(id) });

export const useInbox = (status: QuestionStatus | '', enabled = true) =>
  useQuery({ queryKey: qk.inbox(status), queryFn: () => questionsApi.inbox(status), enabled, refetchInterval: 60_000 });

export const useNutrition = (id: number) =>
  useQuery({ queryKey: qk.nutrition(id), queryFn: () => nutritionApi.overview(id) });

export const useNutritionHistory = (id: number, enabled = true) =>
  useQuery({ queryKey: qk.nutritionHistory(id), queryFn: () => nutritionApi.history(id), enabled });

export const useNutritionSettings = () =>
  useQuery({ queryKey: qk.nutritionSettings, queryFn: nutritionApi.settings, staleTime: 10 * 60_000 });

export const usePrograms = (clientId: number) =>
  useQuery({ queryKey: qk.programs(clientId), queryFn: () => programsApi.listForClient(clientId) });

export const useCurrentProgram = (clientId: number) =>
  useQuery({ queryKey: qk.currentProgram(clientId), queryFn: () => programsApi.current(clientId) });

export const useProgram = (id: number | null) =>
  useQuery({ queryKey: qk.program(id ?? 0), queryFn: () => programsApi.get(id!), enabled: id != null });

export const useProgramTemplates = (enabled = true) =>
  useQuery({ queryKey: qk.templates, queryFn: programsApi.templates, enabled });

export const useExercises = (includeInactive = false) =>
  useQuery({
    queryKey: qk.exercises(includeInactive),
    queryFn: () => programsApi.exercises({ include_inactive: includeInactive }),
    staleTime: 10 * 60_000,
  });

export const useOnboarding = (enabled = true) =>
  useQuery({ queryKey: qk.onboarding, queryFn: onboardingApi.status, enabled, staleTime: 60_000 });

export const useSubscriptions = (clientId: number) =>
  useQuery({ queryKey: qk.subscriptions(clientId), queryFn: () => documentsApi.subscriptions(clientId) });

export const useHealth = (clientId: number) =>
  useQuery({ queryKey: qk.health(clientId), queryFn: () => documentsApi.health(clientId) });

export const useDocuments = (clientId: number) =>
  useQuery({ queryKey: qk.documents(clientId), queryFn: () => documentsApi.documents(clientId) });

export const useStaffPlans = (enabled = true) =>
  useQuery({ queryKey: ['plans'], queryFn: documentsApi.plans, enabled, staleTime: 5 * 60_000 });

export const usePublicSite = () =>
  useQuery({ queryKey: ['public', 'site'], queryFn: siteApi.publicSite, staleTime: 5 * 60_000 });

export const usePublicPlans = () =>
  useQuery({ queryKey: ['public', 'plans'], queryFn: documentsApi.publicPlans, staleTime: 5 * 60_000 });

export const useAdminStats = () => useQuery({ queryKey: qk.adminStats, queryFn: adminApi.stats });

export const useAdminUsers = (role?: Role, q?: string) =>
  useQuery({ queryKey: qk.adminUsers(role, q), queryFn: () => adminApi.users({ role, q: q || undefined }) });

/** Invalidate everything derived from a client's measurements. */
export function useInvalidateClient() {
  const qc = useQueryClient();
  return (clientId: number) =>
    Promise.all([
      qc.invalidateQueries({ queryKey: ['client', clientId] }),
      qc.invalidateQueries({ queryKey: ['clients'] }),
      qc.invalidateQueries({ queryKey: ['session'] }),
      qc.invalidateQueries({ queryKey: ['inbox'] }),
      qc.invalidateQueries({ queryKey: ['admin', 'stats'] }),
    ]);
}
