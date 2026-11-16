/**
 * Telegram groups + AI agents for the coach (ADR-0011).
 * Players never log in: the coach adds them, links their Telegram group, and works from here.
 */
import { api } from './client';
import type { User } from './types';

const data = <T>(p: Promise<{ data: T }>) => p.then((r) => r.data);

export type AgentSource = 'agent' | 'template';
export type DraftStatus = 'pending' | 'approved' | 'rejected';
export type SquatErrorType = 'knees_caving' | 'shallow_depth' | 'back_lean';

export interface GroupCode {
  group_code: string;
  link_command: string;
  expires_at: number;
  linked?: boolean;
}

export interface TelegramClient {
  id: number;
  name: string;
  linked: boolean;
  invite_url: string | null;
  telegram_only: boolean;
}

export interface AgentSummary {
  client_id: number;
  client_name: string;
  facts: Record<string, number | string | null>;
  alerts: ('stalled' | 'no_checkin')[];
  summary_ar: string;
  summary_en: string;
  source: AgentSource;
}

export interface AgentDraft {
  id: number;
  client_id: number;
  text: string;
  source: AgentSource;
  status: DraftStatus;
  created_at: string;
  decided_at: string | null;
  telegram_sent: boolean;
  telegram_linked?: boolean;
  question_id: number | null;
}

export interface SquatCheck {
  id: number;
  client_id: number;
  source: 'telegram' | 'browser';
  status: 'analysed' | 'awaiting_review' | 'failed';
  reps: number | null;
  errors: { rep?: number | null; type: SquatErrorType }[];
  confidence: number | null;
  has_video: boolean;
  created_at: string;
}

export interface SquatCheckInput {
  reps: number;
  errors: { rep?: number | null; type: SquatErrorType }[];
  confidence?: number | null;
}

export interface TelegramPlayerInput {
  full_name: string;
  sex: 'male' | 'female';
  phone?: string | null;
  goal?: string;
  birth_date?: string | null;
  height_cm?: number | null;
  notes?: string | null;
}

export const telegramApi = {
  myTelegram: () => data(api.get<{ linked: boolean; bot_username: string }>('/me/telegram')),
  myTelegramLink: () => data(api.post<{ url: string; expires_at: number }>('/me/telegram/link')),
  clients: () => data(api.get<TelegramClient[]>('/telegram/clients')),
  createPlayer: (body: TelegramPlayerInput) => data(api.post<{ client: User } & GroupCode>('/clients/telegram', body)),
  groupCode: (clientId: number) => data(api.post<GroupCode>(`/clients/${clientId}/telegram/group-code`)),
  unlink: (clientId: number) => api.delete(`/clients/${clientId}/telegram`),

  summary: (clientId: number) => data(api.get<AgentSummary>(`/clients/${clientId}/agent-summary`)),
  drafts: (clientId: number) => data(api.get<AgentDraft[]>(`/clients/${clientId}/agent-drafts`)),
  createDraft: (clientId: number) => data(api.post<AgentDraft>(`/clients/${clientId}/agent-drafts`)),
  draftForQuestion: (questionId: number) => data(api.post<AgentDraft>(`/questions/${questionId}/agent-draft`)),
  approve: (draftId: number, text: string) => data(api.post<AgentDraft>(`/agent-drafts/${draftId}/approve`, { text })),
  reject: (draftId: number) => data(api.post<AgentDraft>(`/agent-drafts/${draftId}/reject`)),

  squatChecks: (clientId: number) => data(api.get<SquatCheck[]>(`/clients/${clientId}/squat-checks`)),
  saveSquatCheck: (clientId: number, body: SquatCheckInput) => data(api.post<SquatCheck>(`/clients/${clientId}/squat-checks`, body)),
  reviewSquatCheck: (checkId: number, body: SquatCheckInput) => data(api.patch<SquatCheck>(`/squat-checks/${checkId}`, body)),
  squatVideo: (checkId: number) => data(api.get<{ url: string }>(`/squat-checks/${checkId}/video`)),
};
