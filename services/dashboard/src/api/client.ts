/** API client for CIS backend services. */

const REVIEW_API = "/api/review";
const POLICY_API = "/api/policy";
const DETECTION_API = "/api/detection";

export interface Case {
  id: string;
  detection_id: string;
  user_id: string;
  thread_id: string;
  status: "open" | "in_review" | "resolved" | "appealed" | "overturned";
  priority: number;
  assigned_to: string | null;
  resolution: string | null;
  resolution_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface CaseListResponse {
  cases: Case[];
  total: number;
  limit: number;
  offset: number;
}

export interface ModerationAction {
  id: string;
  case_id: string;
  actor_id: string;
  actor_role: string;
  action_type: string;
  target_user_id: string;
  target_scope: string;
  reason_code: string;
  metadata: Record<string, unknown>;
  is_permanent: boolean;
  created_at: string;
}

export interface QueueStats {
  open_cases: number;
  in_review_cases: number;
  resolved_today: number;
  avg_resolution_hours: number;
  false_positive_rate: number;
  top_labels: Array<{ label: string; count: number }>;
}

export interface StrikeInfo {
  user_id: string;
  strikes: Array<{
    id: string;
    strike_number: number;
    action_taken: string;
    is_active: boolean;
    window_start: string;
    window_end: string;
  }>;
  total_active: number;
}

export interface ThresholdConfig {
  allow_max: number;
  nudge_min: number;
  nudge_max: number;
  soft_block_min: number;
  soft_block_max: number;
  hard_block_min: number;
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

// Review API
export const reviewApi = {
  listCases: (params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    return fetchJSON<CaseListResponse>(`${REVIEW_API}/cases?${qs}`);
  },

  getCase: (caseId: string) =>
    fetchJSON<Case>(`${REVIEW_API}/cases/${caseId}`),

  updateCase: (caseId: string, body: Record<string, unknown>) =>
    fetchJSON<Case>(`${REVIEW_API}/cases/${caseId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  createAction: (caseId: string, body: Record<string, unknown>) =>
    fetchJSON<ModerationAction>(`${REVIEW_API}/cases/${caseId}/actions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  fileAppeal: (caseId: string, reason: string) =>
    fetchJSON<Case>(`${REVIEW_API}/cases/${caseId}/appeal`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  getStats: (periodDays = 7) =>
    fetchJSON<QueueStats>(`${REVIEW_API}/stats?period_days=${periodDays}`),
};

// Policy API
export const policyApi = {
  getStrikes: (userId: string) =>
    fetchJSON<StrikeInfo>(`${POLICY_API}/strikes/${userId}`),

  getThresholds: () =>
    fetchJSON<ThresholdConfig>(`${POLICY_API}/thresholds`),

  updateThresholds: (body: {
    thresholds: ThresholdConfig;
    changed_by: string;
    reason: string;
  }) =>
    fetchJSON<ThresholdConfig>(`${POLICY_API}/thresholds`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
};
