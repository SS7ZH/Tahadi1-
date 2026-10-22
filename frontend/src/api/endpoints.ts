import { api } from './client';
import type {
  ActivityFactor,
  AdminStats,
  ClientListItem,
  Comment,
  Definition,
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
  ask: (id: number, body: { body: string; session_id?: number | null }) =>
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
