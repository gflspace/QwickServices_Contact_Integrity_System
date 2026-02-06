import { WebSocketServer, WebSocket } from "ws";
import http from "http";
import { v4 as uuidv4 } from "uuid";
import pino from "pino";
import { ChatMessage, InterceptResult } from "./types";
import { getConfig } from "./config";
import { interceptMessage } from "./interceptor";
import { AsyncEmitter } from "./async-emitter";
import { CircuitBreaker, CircuitState } from "./circuit-breaker";

const logger = pino({ name: "interceptor-service" });

/**
 * WebSocket message format for interceptor requests.
 */
interface InterceptorRequest {
  type: "intercept";
  message: ChatMessage;
  request_id?: string;
}

/**
 * WebSocket response format.
 */
interface InterceptorResponse {
  type: "intercept_result";
  request_id: string;
  result: InterceptResult;
  processing_ms: number;
}

/**
 * Error response format.
 */
interface ErrorResponse {
  type: "error";
  request_id?: string;
  error: string;
  message: string;
}

/**
 * Main interceptor service class.
 */
class InterceptorService {
  private wss: WebSocketServer | null = null;
  private httpServer: http.Server | null = null;
  private emitter: AsyncEmitter;
  private circuitBreaker: CircuitBreaker<InterceptResult>;
  private readonly port: number;
  private readonly healthPort: number;

  constructor() {
    const config = getConfig();
    this.port = parseInt(process.env.WS_PORT || "8080", 10);
    this.healthPort = parseInt(process.env.HEALTH_PORT || "8081", 10);

    // Initialize async emitter
    this.emitter = new AsyncEmitter();

    // Initialize circuit breaker
    this.circuitBreaker = new CircuitBreaker<InterceptResult>({
      threshold: config.circuit_breaker_threshold,
      resetTimeout: config.circuit_breaker_reset_ms,
      halfOpenMaxAttempts: 3,
    });

    logger.info(
      {
        ws_port: this.port,
        health_port: this.healthPort,
      },
      "Interceptor service initialized"
    );
  }

  /**
   * Start the WebSocket server and health check endpoint.
   */
  public async start(): Promise<void> {
    // Create WebSocket server
    this.wss = new WebSocketServer({ port: this.port });

    this.wss.on("connection", (ws: WebSocket) => {
      logger.info("Client connected");

      ws.on("message", async (data: Buffer) => {
        await this.handleMessage(ws, data);
      });

      ws.on("close", () => {
        logger.info("Client disconnected");
      });

      ws.on("error", (error: Error) => {
        logger.error({ error: error.message }, "WebSocket error");
      });
    });

    this.wss.on("error", (error: Error) => {
      logger.error({ error: error.message }, "WebSocket server error");
    });

    logger.info({ port: this.port }, "WebSocket server started");

    // Start health check HTTP server
    this.startHealthServer();
  }

  /**
   * Handle incoming WebSocket message.
   */
  private async handleMessage(ws: WebSocket, data: Buffer): Promise<void> {
    const startTime = Date.now();
    let request: InterceptorRequest;

    try {
      // Parse request
      const rawMessage = data.toString();
      request = JSON.parse(rawMessage) as InterceptorRequest;

      // Validate request
      if (request.type !== "intercept") {
        this.sendError(ws, "Invalid request type", request.request_id);
        return;
      }

      if (!request.message || !request.message.content) {
        this.sendError(ws, "Missing message content", request.request_id);
        return;
      }

      const requestId = request.request_id || uuidv4();

      logger.debug(
        {
          request_id: requestId,
          message_id: request.message.message_id,
          user_id: request.message.user_id,
        },
        "Processing intercept request"
      );

      // Execute with circuit breaker
      let result: InterceptResult;

      try {
        const breakerResult = await this.circuitBreaker.execute(() =>
          interceptMessage(request.message)
        );

        if (breakerResult === undefined) {
          // Circuit is open, fail-open (allow message)
          logger.warn(
            {
              request_id: requestId,
              message_id: request.message.message_id,
              circuit_state: this.circuitBreaker.getState(),
            },
            "Circuit breaker open, failing open (allowing message)"
          );

          result = {
            allowed: true,
            action: "allow",
            risk_score: 0.0,
            labels: ["circuit_breaker_open"],
          };
        } else {
          result = breakerResult;
        }
      } catch (error) {
        // Interceptor error, fail-open
        logger.error(
          {
            request_id: requestId,
            message_id: request.message.message_id,
            error: error instanceof Error ? error.message : String(error),
          },
          "Interceptor failed, failing open (allowing message)"
        );

        result = {
          allowed: true,
          action: "allow",
          risk_score: 0.0,
          labels: ["interceptor_error"],
        };
      }

      // Emit async event (fire-and-forget)
      this.emitter.emitAsync(request.message, result);

      // Send response
      const processingMs = Date.now() - startTime;
      const response: InterceptorResponse = {
        type: "intercept_result",
        request_id: requestId,
        result,
        processing_ms: processingMs,
      };

      ws.send(JSON.stringify(response));

      logger.info(
        {
          request_id: requestId,
          message_id: request.message.message_id,
          allowed: result.allowed,
          action: result.action,
          risk_score: result.risk_score,
          processing_ms: processingMs,
        },
        "Intercept request completed"
      );
    } catch (error) {
      logger.error(
        {
          error: error instanceof Error ? error.message : String(error),
        },
        "Error processing message"
      );

      this.sendError(
        ws,
        "Internal server error",
        request?.request_id || undefined
      );
    }
  }

  /**
   * Send error response to client.
   */
  private sendError(
    ws: WebSocket,
    message: string,
    requestId?: string
  ): void {
    const errorResponse: ErrorResponse = {
      type: "error",
      request_id: requestId,
      error: "processing_error",
      message,
    };

    try {
      ws.send(JSON.stringify(errorResponse));
    } catch (error) {
      logger.error(
        { error: error instanceof Error ? error.message : String(error) },
        "Failed to send error response"
      );
    }
  }

  /**
   * Start HTTP health check server.
   */
  private startHealthServer(): void {
    this.httpServer = http.createServer(async (req, res) => {
      if (req.url === "/health" && req.method === "GET") {
        await this.handleHealthCheck(res);
      } else if (req.url === "/metrics" && req.method === "GET") {
        await this.handleMetrics(res);
      } else {
        res.writeHead(404, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Not found" }));
      }
    });

    this.httpServer.listen(this.healthPort, () => {
      logger.info(
        { port: this.healthPort },
        "Health check server started"
      );
    });
  }

  /**
   * Handle health check request.
   */
  private async handleHealthCheck(res: http.ServerResponse): Promise<void> {
    const circuitState = this.circuitBreaker.getState();
    const redisConnected = this.emitter.isConnected();

    const healthy =
      this.wss !== null &&
      (circuitState === CircuitState.CLOSED ||
        circuitState === CircuitState.HALF_OPEN);

    const status = healthy ? 200 : 503;

    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        status: healthy ? "healthy" : "unhealthy",
        timestamp: new Date().toISOString(),
        checks: {
          websocket: this.wss !== null ? "ok" : "down",
          circuit_breaker: circuitState,
          redis: redisConnected ? "connected" : "disconnected",
        },
      })
    );
  }

  /**
   * Handle metrics request.
   */
  private async handleMetrics(res: http.ServerResponse): Promise<void> {
    const streamInfo = await this.emitter.getStreamInfo();

    const metrics = {
      circuit_breaker: {
        state: this.circuitBreaker.getState(),
        failure_count: this.circuitBreaker.getFailureCount(),
      },
      redis: {
        connected: this.emitter.isConnected(),
        stream_length: streamInfo?.length || 0,
        stream_last_id: streamInfo?.lastId || null,
      },
      websocket: {
        active_connections:
          this.wss?.clients.size || 0,
      },
    };

    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(metrics));
  }

  /**
   * Gracefully shutdown the service.
   */
  public async shutdown(): Promise<void> {
    logger.info("Shutting down interceptor service");

    // Close WebSocket server
    if (this.wss) {
      this.wss.close();
      this.wss = null;
    }

    // Close health server
    if (this.httpServer) {
      this.httpServer.close();
      this.httpServer = null;
    }

    // Disconnect async emitter
    await this.emitter.disconnect();

    logger.info("Interceptor service shutdown complete");
  }
}

// Main entry point
async function main(): Promise<void> {
  logger.info("Starting Contact Integrity System - Interceptor Service");

  const service = new InterceptorService();

  // Handle shutdown signals
  const shutdown = async () => {
    logger.info("Received shutdown signal");
    await service.shutdown();
    process.exit(0);
  };

  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);

  // Handle uncaught errors
  process.on("uncaughtException", (error: Error) => {
    logger.fatal({ error: error.message, stack: error.stack }, "Uncaught exception");
    process.exit(1);
  });

  process.on("unhandledRejection", (reason: unknown) => {
    logger.fatal(
      {
        reason: reason instanceof Error ? reason.message : String(reason),
      },
      "Unhandled rejection"
    );
    process.exit(1);
  });

  // Start service
  await service.start();

  logger.info("Interceptor service ready");
}

// Run if executed directly
if (require.main === module) {
  main().catch((error) => {
    logger.fatal(
      { error: error instanceof Error ? error.message : String(error) },
      "Failed to start service"
    );
    process.exit(1);
  });
}

export { InterceptorService };
