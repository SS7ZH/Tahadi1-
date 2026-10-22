import { api } from './client';
import type {
  ActivityFactor,
  AdminStats,
  ClientListItem,
  Comment,
  Definition,
  HealthDeclarationInfo,
  HealthInput,
  MedicalFileInfo,
  OnboardingStatus,
  Plan,
  RenderedTemplate,
  SignedDocumentInfo,
  SubscriptionInfo,
  TemplateKind,
  TemplateVersion,
  Exercise,
  Program,
  ProgramInput,
  ProgramSummary,
  NutritionOverview,
  NutritionPlan,
  NutritionPlanInput,
  NutritionSettingRow,
  Progress,
  Question,
  QuestionStatus,
  Role,
  SessionDetail,
  Session,
  SessionInput,
  Summary,
  TokenPair,
  User,
} from './types';

const data = <T>(p: Promise<{ data: T }>) => p.then((r) => r.data);

export const authApi = {
  login: (email: string, password: string) => data(api.post<TokenPair>('/auth/login', { email, password })),
  me: () => data(api.get<User>('/auth/me')),
  updateMe: (body: { full_name?: string; phone?: string; current_password?: string; new_password?: string }) =>
    data(api.patch<User>('/auth/me', body)),
};

export const referenceApi = {
  definitions: () => data(api.get<Definition[]>('/measurement-definitions')),
  activityFactors: () => data(api.get<ActivityFactor[]>('/activity-factors')),
};

export interface ClientCreateBody {
  full_name: string;
  email: string;
  phone?: string | null;
  password: string;
  sex: string;
  birth_date: string;
  height_cm: number;
  goal: string;
  activity_key: string;
  notes?: string | null;
  trainer_id?: number | null;
}

export const clientsApi = {
  list: (params?: { q?: string; trainer_id?: number }) => data(api.get<ClientListItem[]>('/clients', { params })),
  get: (id: number) => data(api.get<User>(`/clients/${id}`)),
  create: (body: ClientCreateBody) => data(api.post<User>('/clients', body)),
  update: (id: number, body: Partial<ClientCreateBody> & { is_active?: boolean }) =>
    data(api.patch<User>(`/clients/${id}`, body)),
  summary: (id: number) => data(api.get<Summary>(`/clients/${id}/summary`)),
  progress: (id: number, keys?: string[]) =>
    data(api.get<Progress>(`/clients/${id}/progress`, { params: keys?.length ? { keys: keys.join(',') } : {} })),
  sessions: (id: number) => data(api.get<Session[]>(`/clients/${id}/sessions`)),
  createSession: (id: number, body: SessionInput) => data(api.post<SessionDetail>(`/clients/${id}/sessions`, body)),
  comments: (id: number) => data(api.get<Comment[]>(`/clients/${id}/comments`)),
  addComment: (id: number, body: { body: string; session_id?: number | null }) =>
    data(api.post<Comment>(`/clients/${id}/comments`, body)),
  questions: (id: number) => data(api.get<Question[]>(`/clients/${id}/questions`)),
  ask: (id: number, body: { body: string; session_id?: number | null; program_day_id?: number | null }) =>
    data(api.post<Question>(`/clients/${id}/questions`, body)),
};

export const sessionsApi = {
  get: (id: number) => data(api.get<SessionDetail>(`/sessions/${id}`)),
  update: (id: number, body: SessionInput) => data(api.put<SessionDetail>(`/sessions/${id}`, body)),
  remove: (id: number) => api.delete(`/sessions/${id}`),
};

export const commentsApi = {
  remove: (id: number) => api.delete(`/comments/${id}`),
};

export const questionsApi = {
  reply: (id: number, body: string) => data(api.post<Question>(`/questions/${id}/replies`, { body })),
  setStatus: (id: number, status: QuestionStatus) => data(api.patch<Question>(`/questions/${id}`, { status })),
  inbox: (status?: QuestionStatus | '') =>
    data(api.get<Question[]>('/trainer/questions', { params: { status: status ?? '' } })),
};

export interface AdminUserBody {
  full_name?: string;
  email?: string;
  phone?: string | null;
  password?: string;
  role?: Role;
  is_active?: boolean;
  sex?: string;
  birth_date?: string;
  height_cm?: number;
  goal?: string;
  activity_key?: string;
  notes?: string | null;
  trainer_id?: number | null;
}

export const adminApi = {
  stats: () => data(api.get<AdminStats>('/admin/stats')),
  users: (params?: { role?: Role; q?: string }) => data(api.get<User[]>('/admin/users', { params })),
  createUser: (body: AdminUserBody) => data(api.post<User>('/admin/users', body)),
  updateUser: (id: number, body: AdminUserBody) => data(api.patch<User>(`/admin/users/${id}`, body)),
  deleteUser: (id: number) => api.delete(`/admin/users/${id}`),
  assignTrainer: (clientId: number, trainerId: number | null) =>
    data(api.patch<User>(`/admin/clients/${clientId}/assign-trainer`, { trainer_id: trainerId })),
  definitions: () => data(api.get<Definition[]>('/admin/measurement-definitions')),
  createDefinition: (body: Partial<Definition>) => data(api.post<Definition>('/admin/measurement-definitions', body)),
  updateDefinition: (id: number, body: Partial<Definition>) =>
    data(api.patch<Definition>(`/admin/measurement-definitions/${id}`, body)),
  activityFactors: () => data(api.get<ActivityFactor[]>('/admin/activity-factors')),
  updateActivityFactor: (id: number, body: Partial<ActivityFactor>) =>
    data(api.patch<ActivityFactor>(`/admin/activity-factors/${id}`, body)),
};

export const nutritionApi = {
  overview: (clientId: number) => data(api.get<NutritionOverview>(`/clients/${clientId}/nutrition`)),
  history: (clientId: number) => data(api.get<NutritionPlan[]>(`/clients/${clientId}/nutrition/history`)),
  save: (clientId: number, body: NutritionPlanInput) =>
    data(api.post<NutritionOverview>(`/clients/${clientId}/nutrition`, body)),
  settings: () => data(api.get<NutritionSettingRow[]>('/nutrition-settings')),
  updateSetting: (id: number, body: Partial<NutritionSettingRow>) =>
    data(api.patch<NutritionSettingRow>(`/admin/nutrition-settings/${id}`, body)),
};

export const programsApi = {
  exercises: (params?: { q?: string; muscle_group?: string; include_inactive?: boolean }) =>
    data(api.get<Exercise[]>('/exercises', { params })),
  createExercise: (body: Partial<Exercise>) => data(api.post<Exercise>('/admin/exercises', body)),
  updateExercise: (id: number, body: Partial<Exercise>) => data(api.patch<Exercise>(`/admin/exercises/${id}`, body)),
  listForClient: (clientId: number) => data(api.get<ProgramSummary[]>(`/clients/${clientId}/programs`)),
  current: (clientId: number) => data(api.get<Program | null>(`/clients/${clientId}/program/current`)),
  create: (clientId: number, body: ProgramInput) => data(api.post<Program>(`/clients/${clientId}/programs`, body)),
  templates: () => data(api.get<ProgramSummary[]>('/program-templates')),
  get: (id: number) => data(api.get<Program>(`/programs/${id}`)),
  update: (id: number, body: ProgramInput) => data(api.put<Program>(`/programs/${id}`, body)),
  remove: (id: number) => api.delete(`/programs/${id}`),
  activate: (id: number) => data(api.post<Program>(`/programs/${id}/activate`)),
  archive: (id: number) => data(api.post<Program>(`/programs/${id}/archive`)),
  duplicate: (id: number, body: { client_id?: number; as_template?: boolean; title?: string }) =>
    data(api.post<Program>(`/programs/${id}/duplicate`, body)),
};

export const onboardingApi = {
  status: () => data(api.get<OnboardingStatus>('/onboarding')),
  chooseSubscription: (plan_id: number, start_date: string) =>
    data(api.post<SubscriptionInfo>('/onboarding/subscription', { plan_id, start_date })),
  uploadFile: (file: File, later = false) => {
    const form = new FormData();
    form.append('file', file);
    return data(api.post<MedicalFileInfo>(later ? '/me/files' : '/onboarding/files', form, { timeout: 120_000 }));
  },
  removeFile: (id: number) => api.delete(`/onboarding/files/${id}`),
  disclaimer: () => data(api.get<RenderedTemplate>('/onboarding/disclaimer')),
  contract: () => data(api.get<RenderedTemplate>('/onboarding/contract')),
  submitHealth: (body: HealthInput & { template_id: number; typed_name: string; agreed: boolean }) =>
    data(api.post<OnboardingStatus>('/onboarding/health', body)),
  signContract: (body: { template_id: number; typed_name: string; agreed: boolean }) =>
    data(api.post<OnboardingStatus>('/onboarding/contract', body)),
  updateHealth: (body: HealthInput) => data(api.post<HealthDeclarationInfo>('/me/health-declaration', body)),
};

export const documentsApi = {
  subscriptions: (clientId: number) =>
    data(api.get<{ current: SubscriptionInfo | null; history: SubscriptionInfo[] }>(`/clients/${clientId}/subscriptions`)),
  renew: (clientId: number, body: { plan_id: number; start_date: string; kind: 'renewal' | 'change' }) =>
    data(api.post<SubscriptionInfo>(`/clients/${clientId}/subscriptions`, body)),
  updateSubscription: (id: number, body: { start_date?: string; end_date?: string }) =>
    data(api.patch<SubscriptionInfo>(`/subscriptions/${id}`, body)),
  health: (clientId: number) =>
    data(
      api.get<{ current: HealthDeclarationInfo | null; history: HealthDeclarationInfo[]; needs_review: boolean }>(
        `/clients/${clientId}/health`,
      ),
    ),
  review: (clientId: number) => api.post(`/clients/${clientId}/health/review`),
  documents: (clientId: number) => data(api.get<SignedDocumentInfo[]>(`/clients/${clientId}/documents`)),
  fileUrl: (fileId: number) => data(api.get<{ url: string; expires_in: number; name: string }>(`/files/${fileId}/url`)),
  plans: () => data(api.get<Plan[]>('/plans')),
  publicPlans: () => data(api.get<Plan[]>('/public/plans')),
  adminPlans: () => data(api.get<Plan[]>('/admin/plans')),
  createPlan: (body: Partial<Plan>) => data(api.post<Plan>('/admin/plans', body)),
  updatePlan: (id: number, body: Partial<Plan> & { clear_price?: boolean }) =>
    data(api.patch<Plan>(`/admin/plans/${id}`, body)),
  templates: (kind: TemplateKind) =>
    data(api.get<{ placeholders: string[]; versions: TemplateVersion[] }>('/admin/templates', { params: { kind } })),
  newTemplateVersion: (body: { kind: TemplateKind; body_ar: string; body_en: string }) =>
    data(api.post<TemplateVersion>('/admin/templates', body)),
};
