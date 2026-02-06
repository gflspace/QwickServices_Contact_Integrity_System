import { InterceptorConfig } from "./types";

/**
 * Load configuration from environment variables with production-grade defaults.
 * All values are validated and typed correctly.
 */
export function loadConfig(): InterceptorConfig {
  const config: InterceptorConfig = {
    sync_threshold: parseFloat(process.env.SYNC_THRESHOLD || "0.65"),
    redis_host: process.env.REDIS_HOST || "localhost",
    redis_port: parseInt(process.env.REDIS_PORT || "6379", 10),
    detection_host: process.env.DETECTION_HOST || "localhost",
    detection_port: parseInt(process.env.DETECTION_PORT || "8000", 10),
    circuit_breaker_threshold: parseInt(
      process.env.CIRCUIT_BREAKER_THRESHOLD || "5",
      10
    ),
    circuit_breaker_reset_ms: parseInt(
      process.env.CIRCUIT_BREAKER_RESET_MS || "30000",
      10
    ),
    max_message_length: parseInt(
      process.env.MAX_MESSAGE_LENGTH || "10000",
      10
    ),
  };

  // Validation
  if (config.sync_threshold < 0 || config.sync_threshold > 1) {
    throw new Error(
      `Invalid sync_threshold: ${config.sync_threshold}. Must be between 0 and 1.`
    );
  }

  if (config.redis_port < 1 || config.redis_port > 65535) {
    throw new Error(`Invalid redis_port: ${config.redis_port}`);
  }

  if (config.detection_port < 1 || config.detection_port > 65535) {
    throw new Error(`Invalid detection_port: ${config.detection_port}`);
  }

  if (config.circuit_breaker_threshold < 1) {
    throw new Error(
      `Invalid circuit_breaker_threshold: ${config.circuit_breaker_threshold}`
    );
  }

  if (config.circuit_breaker_reset_ms < 1000) {
    throw new Error(
      `Invalid circuit_breaker_reset_ms: ${config.circuit_breaker_reset_ms}. Must be at least 1000ms.`
    );
  }

  if (config.max_message_length < 1) {
    throw new Error(
      `Invalid max_message_length: ${config.max_message_length}`
    );
  }

  return config;
}

/**
 * Get current configuration instance.
 * Cached after first load for performance.
 */
let cachedConfig: InterceptorConfig | null = null;

export function getConfig(): InterceptorConfig {
  if (!cachedConfig) {
    cachedConfig = loadConfig();
  }
  return cachedConfig;
}

/**
 * Reset cached config (useful for testing).
 */
export function resetConfig(): void {
  cachedConfig = null;
}
