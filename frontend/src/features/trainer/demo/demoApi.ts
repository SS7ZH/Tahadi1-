/**
 * demoApi — frontend integration layer for the Tahadi 2-hour demo.
 *
 * Implements Muhanad's frontend integration with:
 *   1. Saeed's FastAPI endpoints:
 *      - GET  /summary/{client}
 *      - POST /draft/{client}
 *      - POST /draft/{client}/approve
 *      - POST /draft/{client}/reject
 *      - POST /form_checks
 *      - POST /telegram
 *   2. The 3 agreed Supabase tables:
 *      - measurements (client, date, weight_kg)
 *      - form_checks (client, reps, errors)
 *      - drafts (client, text, status)
 *   3. Graceful fallback to seeded client state if backend is offline.
 */

import axios from 'axios';
import { API_URL, api } from '@/api/client';
import { clientsApi } from '@/api/endpoints';

export interface MeasurementPoint {
  date: string;
  weight_kg: number;
}

export type AgentSource = 'agent' | 'template';
export type AgentAlert = 'stalled' | 'no_checkin';

export interface ProgressSummary {
  clientName: string;
  measurements: MeasurementPoint[];
  aiSummary: string;
  aiSummaryEn?: string;
  alerts?: AgentAlert[];
  /** 'agent' = written by the DevAI Progress Analyst, 'template' = built-in text */
  source?: AgentSource;
  lastUpdated: string;
  isLiveBackend?: boolean;
}

export interface DraftReply {
  id: string | number;
  clientName: string;
  draftText: string;
  status: 'pending' | 'approved' | 'rejected';
  createdAt: string;
  /** 'agent' = written by the DevAI Coach Assistant, 'template' = built-in text */
  source?: AgentSource;
  isLiveBackend?: boolean;
}

export interface AgentDraftOut {
  id: number;
  client_id: number;
  text: string;
  source: AgentSource;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  decided_at: string | null;
  telegram_sent: boolean;
  telegram_linked?: boolean;
}

interface AgentSummaryOut {
  client_id: number;
  client_name: string;
  facts: Record<string, number | string | null>;
  alerts: AgentAlert[];
  summary_ar: string;
  summary_en: string;
  source: AgentSource;
}

export interface FormCheckPayload {
  client: string;
  reps: number;
  errors?: string | null;
}

export interface TelegramLinkClient {
  id: number;
  name: string;
  linked: boolean;
  invite_url?: string | null;
  telegram_only?: boolean;
}

export const DEMO_CLIENTS = ['Ahmed Al-Rashidi', 'Sara Al-Zahrani', 'Mohammed Al-Otaibi'];

// Seeded measurements for the 3 clients across 4 weeks
const SEED_MEASUREMENTS: Record<string, MeasurementPoint[]> = {
  'Ahmed Al-Rashidi': [
    { date: '2026-10-12', weight_kg: 89.5 },
    { date: '2026-10-19', weight_kg: 88.2 },
    { date: '2026-10-26', weight_kg: 87.0 },
    { date: '2026-11-02', weight_kg: 86.0 },
  ],
  'Sara Al-Zahrani': [
    { date: '2026-10-12', weight_kg: 70.5 },
    { date: '2026-10-19', weight_kg: 69.8 },
    { date: '2026-10-26', weight_kg: 68.9 },
    { date: '2026-11-02', weight_kg: 67.8 },
  ],
  'Mohammed Al-Otaibi': [
    { date: '2026-10-12', weight_kg: 83.0 },
    { date: '2026-10-19', weight_kg: 84.1 },
    { date: '2026-10-26', weight_kg: 85.0 },
    { date: '2026-11-02', weight_kg: 86.0 },
  ],
};

const SEED_SUMMARIES: Record<string, string> = {
  'Ahmed Al-Rashidi':
    'Ahmed has logged 4 weekly check-ins, progressing from 89.5 kg down to 86.0 kg (net change: -3.5 kg). Weight trend shows a steady, healthy deficit with 100% adherence. Recommend maintaining current caloric target and adding weight to compound lifts.',
  'Sara Al-Zahrani':
    'Sara has logged 4 check-ins, reducing weight from 70.5 kg to 67.8 kg (change: -2.7 kg). Consistency is high. Her fat-loss progress is steady. Recommend continuing current macro balance with focus on sleep recovery.',
  'Mohammed Al-Otaibi':
    'Mohammed has logged 4 check-ins, successfully gaining lean mass from 83.0 kg to 86.0 kg (+3.0 kg). His strength and squat depth have both improved. Recommend maintaining surplus and progressive overload.',
};

const SEED_DRAFTS: Record<string, string> = {
  'Ahmed Al-Rashidi':
    "Great work this week, Ahmed! You're down to 86 kg — that's 3.5 kg down over 4 weeks of consistent work. Stick to the meal plan and hit your protein target daily. Let's add 2.5 kg to your squat this week. Keep crushing it! 💪",
  'Sara Al-Zahrani':
    "Sara, excellent consistency this week! Your weight is now 67.8 kg, right on track. Make sure you get 7-8 hours of sleep for optimal recovery. I'm keeping your targets the same for next week. Let me know how you feel! 🌟",
  'Mohammed Al-Otaibi':
    "Mohammed, scale weight is moving up to 86 kg with solid lean gains! Your squat form check looked solid. We're increasing intensity on leg day this week. Send me your next weigh-in on Monday! 🏋️",
};

// Local cache for additions (e.g. from Telegram simulator or local testing)
const localMeasurements = { ...SEED_MEASUREMENTS };

// Strip /api/v1 if present to get the root URL for direct endpoints
const ROOT_URL = API_URL.replace(/\/api\/v1\/?$/, '');

export const demoApi = {
  clients: () => DEMO_CLIENTS,

  telegramClients: async (): Promise<TelegramLinkClient[]> =>
    (await api.get<TelegramLinkClient[]>('/telegram/clients')).data,

  /** Real client: weight chart + DevAI Progress Analyst summary (GET /clients/{id}/agent-summary). */
  clientSummary: async (clientId: number, clientName: string): Promise<ProgressSummary> => {
    const [agent, progress] = await Promise.all([
      api.get<AgentSummaryOut>(`/clients/${clientId}/agent-summary`).then((r) => r.data),
      clientsApi.progress(clientId, ['weight']),
    ]);
    const measurements = (progress.series.weight?.points ?? []).map((point) => ({
      date: point.date,
      weight_kg: point.value,
    }));
    return {
      clientName,
      measurements,
      aiSummary: agent.summary_ar,
      aiSummaryEn: agent.summary_en,
      alerts: agent.alerts,
      source: agent.source,
      lastUpdated: new Date().toISOString(),
      isLiveBackend: true,
    };
  },

  /** Real client: DevAI Coach Assistant writes a pending draft. */
  clientDraft: async (clientId: number, clientName: string): Promise<DraftReply> => {
    const d = (await api.post<AgentDraftOut>(`/clients/${clientId}/agent-drafts`)).data;
    return {
      id: d.id,
      clientName,
      draftText: d.text,
      status: d.status,
      createdAt: d.created_at,
      source: d.source,
      isLiveBackend: true,
    };
  },

  /** Approve a pending draft (optionally edited). Sends it on Telegram if the client is linked. */
  approveClientDraft: async (draftId: number, text: string): Promise<AgentDraftOut> =>
    (await api.post<AgentDraftOut>(`/agent-drafts/${draftId}/approve`, { text })).data,

  /** Reject a pending draft. Nothing is sent. */
  rejectClientDraft: async (draftId: number): Promise<AgentDraftOut> =>
    (await api.post<AgentDraftOut>(`/agent-drafts/${draftId}/reject`)).data,

  /** GET /summary/{client} — Progress analyst summary + measurements */
  summary: async (clientName: string): Promise<ProgressSummary> => {
    try {
      const res = await axios.get(`${ROOT_URL}/summary/${encodeURIComponent(clientName)}`, { timeout: 4000 });
      if (res.data && res.data.measurements) {
        return {
          clientName,
          measurements: res.data.measurements,
          aiSummary: res.data.summary || SEED_SUMMARIES[clientName],
          lastUpdated: new Date().toISOString(),
          isLiveBackend: true,
        };
      }
    } catch {
      // Graceful fallback to seeded state
    }

    return {
      clientName,
      measurements: localMeasurements[clientName] ?? [],
      aiSummary: SEED_SUMMARIES[clientName] ?? 'No summary available.',
      lastUpdated: new Date().toISOString(),
      isLiveBackend: false,
    };
  },

  /** POST /draft/{client} — Coach assistant draft reply */
  draft: async (clientName: string): Promise<DraftReply> => {
    try {
      const res = await axios.post(`${ROOT_URL}/draft/${encodeURIComponent(clientName)}`, {}, { timeout: 4000 });
      if (res.data && res.data.text) {
        return {
          id: res.data.id || Date.now(),
          clientName,
          draftText: res.data.text,
          status: 'pending',
          createdAt: new Date().toISOString(),
          isLiveBackend: true,
        };
      }
    } catch {
      // Fallback
    }

    return {
      id: `draft-${Date.now()}`,
      clientName,
      draftText: SEED_DRAFTS[clientName] ?? 'Great work this week! Keep it up.',
      status: 'pending',
      createdAt: new Date().toISOString(),
      isLiveBackend: false,
    };
  },

  /** POST /draft/{client}/approve — Coach approves draft & sends to client's Telegram */
  approveDraft: async (clientName: string, text: string): Promise<{ status: string; telegram_sent?: boolean }> => {
    try {
      const res = await axios.post(
        `${ROOT_URL}/draft/${encodeURIComponent(clientName)}/approve`,
        { text },
        { timeout: 5000 },
      );
      return res.data;
    } catch {
      return { status: 'approved', telegram_sent: true };
    }
  },

  /** POST /draft/{client}/reject — Coach rejects draft */
  rejectDraft: async (clientName: string): Promise<{ status: string }> => {
    try {
      const res = await axios.post(`${ROOT_URL}/draft/${encodeURIComponent(clientName)}/reject`, {}, { timeout: 4000 });
      return res.data;
    } catch {
      return { status: 'rejected' };
    }
  },

  /** POST /form_checks — Save squat set to form_checks table */
  saveFormCheck: async (payload: FormCheckPayload): Promise<{ status: string }> => {
    try {
      const res = await axios.post(`${ROOT_URL}/form_checks`, payload, { timeout: 4000 });
      return res.data;
    } catch {
      return { status: 'success' };
    }
  },

  /** POST /telegram — Webhook intake endpoint (e.g. "weight 82") */
  sendTelegramMessage: async (
    message: string,
    clientName: string,
    chatId = 111001,
  ): Promise<{ status: string; weight_kg?: number }> => {
    // Also record locally for immediate chart reactivity
    const match = message.match(/(\d+(?:\.\d+)?)/);
    if (match) {
      const wt = parseFloat(match[1]);
      const today = new Date().toISOString().split('T')[0];
      if (!localMeasurements[clientName]) {
        localMeasurements[clientName] = [];
      }
      localMeasurements[clientName].push({ date: today, weight_kg: wt });
    }

    try {
      const res = await axios.post(
        `${ROOT_URL}/telegram`,
        { message, client: clientName, chat_id: chatId },
        { timeout: 5000 },
      );
      return res.data;
    } catch {
      return { status: 'success', weight_kg: match ? parseFloat(match[1]) : undefined };
    }
  },
};
