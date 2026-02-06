import Redis from "ioredis";
import { ChatMessage, InterceptResult } from "./types";
import { getConfig } from "./config";
import pino from "pino";

const logger = pino({ name: "async-emitter" });

/**
 * Redis stream event payload for async processing.
 */
interface StreamEvent {
  message_id: string;
  thread_id: string;
  user_id: string;
  content: string;
  timestamp: string;
  gps_lat?: number;
  gps_lon?: number;
  intercept_result: {
    allowed: boolean;
    action: string;
    risk_score: number;
    labels: string[];
  };
  emitted_at: string;
}

/**
 * AsyncEmitter handles publishing intercepted messages to Redis Stream
 * for asynchronous processing by the detection service.
 *
 * Design principles:
 * - Fail-open: if Redis is unavailable, log and continue
 * - Non-blocking: never block the interceptor path
 * - Resilient: automatic reconnection and error handling
 */
export class AsyncEmitter {
  private redis: Redis | null = null;
  private connected: boolean = false;
  private readonly streamKey = "cis:messages";
  private reconnectTimer: NodeJS.Timeout | null = null;

  constructor() {
    this.connect();
  }

  /**
   * Establish connection to Redis with error handling.
   */
  private connect(): void {
    try {
      const config = getConfig();

      this.redis = new Redis({
        host: config.redis_host,
        port: config.redis_port,
        retryStrategy: (times: number) => {
          // Exponential backoff: 1s, 2s, 4s, 8s, max 10s
          const delay = Math.min(Math.pow(2, times) * 1000, 10000);
          logger.info({ attempt: times, delay_ms: delay }, "Redis reconnecting");
          return delay;
        },
        maxRetriesPerRequest: 3,
        enableReadyCheck: true,
        enableOfflineQueue: false, // Fail fast if not connected
      });

      this.redis.on("connect", () => {
        logger.info("Redis connected");
        this.connected = true;
      });

      this.redis.on("ready", () => {
        logger.info("Redis ready");
        this.connected = true;
      });

      this.redis.on("error", (error: Error) => {
        logger.error({ error: error.message }, "Redis connection error");
        this.connected = false;
      });

      this.redis.on("close", () => {
        logger.warn("Redis connection closed");
        this.connected = false;
      });

      this.redis.on("reconnecting", () => {
        logger.info("Redis reconnecting");
        this.connected = false;
      });
    } catch (error) {
      logger.error(
        { error: error instanceof Error ? error.message : String(error) },
        "Failed to initialize Redis client"
      );
      this.connected = false;
      this.scheduleReconnect();
    }
  }

  /**
   * Schedule reconnection attempt after failure.
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return;
    }

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      logger.info("Attempting to reconnect to Redis");
      this.connect();
    }, 5000);
  }

  /**
   * Check if Redis is connected and ready.
   */
  public isConnected(): boolean {
    return this.connected && this.redis !== null;
  }

  /**
   * Emit message to Redis Stream for async processing.
   *
   * @param message - The original chat message
   * @param interceptResult - The result from the interceptor
   */
  public async emit(
    message: ChatMessage,
    interceptResult: InterceptResult
  ): Promise<void> {
    // Fail-open if Redis unavailable
    if (!this.isConnected() || !this.redis) {
      logger.warn(
        { message_id: message.message_id },
        "Redis not connected, skipping async emit (fail-open)"
      );
      return;
    }

    try {
      const event: StreamEvent = {
        message_id: message.message_id,
        thread_id: message.thread_id,
        user_id: message.user_id,
        content: message.content,
        timestamp: message.timestamp,
        gps_lat: message.gps_lat,
        gps_lon: message.gps_lon,
        intercept_result: {
          allowed: interceptResult.allowed,
          action: interceptResult.action,
          risk_score: interceptResult.risk_score,
          labels: interceptResult.labels,
        },
        emitted_at: new Date().toISOString(),
      };

      // Serialize event to flat key-value pairs for Redis Stream
      const streamData: Record<string, string> = {
        message_id: event.message_id,
        thread_id: event.thread_id,
        user_id: event.user_id,
        content: event.content,
        timestamp: event.timestamp,
        intercept_result: JSON.stringify(event.intercept_result),
        emitted_at: event.emitted_at,
      };

      if (event.gps_lat !== undefined) {
        streamData.gps_lat = event.gps_lat.toString();
      }
      if (event.gps_lon !== undefined) {
        streamData.gps_lon = event.gps_lon.toString();
      }

      // Use XADD to append to stream
      const messageId = await this.redis.xadd(
        this.streamKey,
        "*", // Auto-generate ID
        ...Object.entries(streamData).flat()
      );

      logger.debug(
        {
          message_id: message.message_id,
          stream_id: messageId,
          risk_score: interceptResult.risk_score,
        },
        "Message emitted to stream"
      );
    } catch (error) {
      // Fail-open: log error but don't throw
      logger.error(
        {
          message_id: message.message_id,
          error: error instanceof Error ? error.message : String(error),
        },
        "Failed to emit message to Redis stream (fail-open)"
      );
    }
  }

  /**
   * Emit message with fire-and-forget semantics.
   * Does not wait for completion or handle errors externally.
   */
  public emitAsync(
    message: ChatMessage,
    interceptResult: InterceptResult
  ): void {
    // Fire and forget
    this.emit(message, interceptResult).catch((error) => {
      logger.error(
        {
          message_id: message.message_id,
          error: error instanceof Error ? error.message : String(error),
        },
        "Unhandled error in async emit"
      );
    });
  }

  /**
   * Gracefully disconnect from Redis.
   */
  public async disconnect(): Promise<void> {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.redis) {
      try {
        await this.redis.quit();
        logger.info("Redis disconnected gracefully");
      } catch (error) {
        logger.error(
          { error: error instanceof Error ? error.message : String(error) },
          "Error during Redis disconnect"
        );
      }
      this.redis = null;
      this.connected = false;
    }
  }

  /**
   * Get stream statistics (for monitoring).
   */
  public async getStreamInfo(): Promise<{
    length: number;
    lastId: string;
  } | null> {
    if (!this.isConnected() || !this.redis) {
      return null;
    }

    try {
      const info = await this.redis.xinfo("STREAM", this.streamKey);
      // Parse XINFO response (array format)
      const length = info[1] as number;
      const lastId = info[3] as string;

      return { length, lastId };
    } catch (error) {
      logger.error(
        { error: error instanceof Error ? error.message : String(error) },
        "Failed to get stream info"
      );
      return null;
    }
  }
}
