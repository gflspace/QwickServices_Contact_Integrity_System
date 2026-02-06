/** Shared TypeScript types for the Contact Integrity System */

export interface ChatMessage {
  message_id: string;
  thread_id: string;
  user_id: string;
  content: string;
  timestamp: string;
  gps_lat?: number;
  gps_lon?: number;
}

export interface AnalyzeRequest {
  message_id: string;
  thread_id: string;
  user_id: string;
  content: string;
  context_messages?: ContextMessage[];
  gps_lat?: number;
  gps_lon?: number;
  stages?: number[];
}

export interface ContextMessage {
  content: string;
  user_id: string;
  timestamp: string;
}

export interface EvidenceSpan {
  offset: number;
  length: number;
  type: "phone" | "email" | "url" | "social" | "intent" | "obfuscation";
  confidence?: number;
}

export interface AnalyzeResponse {
  detection_id: string;
  message_id: string;
  risk_score: number;
  labels: string[];
  evidence_spans: EvidenceSpan[];
  hashed_tokens: string[];
  stage: number;
  ruleset_version: string;
  model_version?: string;
  processing_ms: number;
}

export interface EnforceResponse {
  action:
    | "allow"
    | "nudge"
    | "soft_block"
    | "hard_block"
    | "warning"
    | "cooldown"
    | "restriction"
    | "suspension_candidate";
  risk_band: "low" | "medium" | "high" | "critical";
  strike_count: number;
  strike_id?: string;
  case_id?: string;
  enforcement_details?: {
    duration_hours?: number;
    message: string;
    scope: "message" | "thread" | "account";
  };
}

export interface InterceptResult {
  allowed: boolean;
  action: string;
  risk_score: number;
  labels: string[];
  nudge_message?: string;
  block_reason?: string;
}

export type RiskBand = "low" | "medium" | "high" | "critical";

export interface InterceptorConfig {
  sync_threshold: number;
  redis_host: string;
  redis_port: number;
  detection_host: string;
  detection_port: number;
  circuit_breaker_threshold: number;
  circuit_breaker_reset_ms: number;
  max_message_length: number;
}
