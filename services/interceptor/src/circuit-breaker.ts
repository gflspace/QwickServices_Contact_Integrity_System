import pino from "pino";

const logger = pino({ name: "circuit-breaker" });

/**
 * Circuit breaker states.
 */
export enum CircuitState {
  CLOSED = "closed", // Normal operation
  OPEN = "open", // Failing, rejecting requests
  HALF_OPEN = "half_open", // Testing if service recovered
}

/**
 * Circuit breaker configuration.
 */
export interface CircuitBreakerConfig {
  threshold: number; // Number of consecutive failures before opening
  resetTimeout: number; // Time in ms before attempting to close circuit
  halfOpenMaxAttempts?: number; // Max attempts in half-open state (default: 1)
}

/**
 * Circuit breaker for protecting against cascading failures.
 *
 * States:
 * - CLOSED: Normal operation, requests pass through
 * - OPEN: Too many failures, requests fail fast
 * - HALF_OPEN: Testing recovery, limited requests pass through
 *
 * This implementation uses fail-open semantics for the interceptor:
 * when circuit is open, allow all messages to prevent blocking legitimate traffic.
 */
export class CircuitBreaker<T> {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount: number = 0;
  private successCount: number = 0;
  private lastFailureTime: number = 0;
  private readonly config: Required<CircuitBreakerConfig>;

  constructor(config: CircuitBreakerConfig) {
    this.config = {
      ...config,
      halfOpenMaxAttempts: config.halfOpenMaxAttempts || 1,
    };

    logger.info(
      {
        threshold: this.config.threshold,
        reset_timeout_ms: this.config.resetTimeout,
      },
      "Circuit breaker initialized"
    );
  }

  /**
   * Get current circuit state.
   */
  public getState(): CircuitState {
    return this.state;
  }

  /**
   * Get failure count.
   */
  public getFailureCount(): number {
    return this.failureCount;
  }

  /**
   * Execute function with circuit breaker protection.
   *
   * @param fn - Function to execute
   * @returns Result of function or undefined if circuit is open
   */
  public async execute(fn: () => Promise<T>): Promise<T | undefined> {
    // Check if we should transition from OPEN to HALF_OPEN
    if (this.state === CircuitState.OPEN) {
      const timeSinceFailure = Date.now() - this.lastFailureTime;
      if (timeSinceFailure >= this.config.resetTimeout) {
        logger.info("Circuit breaker transitioning to HALF_OPEN");
        this.state = CircuitState.HALF_OPEN;
        this.successCount = 0;
      } else {
        logger.warn(
          {
            state: this.state,
            failures: this.failureCount,
            time_until_retry_ms: this.config.resetTimeout - timeSinceFailure,
          },
          "Circuit breaker is OPEN, failing fast"
        );
        return undefined; // Fail fast
      }
    }

    // In HALF_OPEN, limit attempts
    if (
      this.state === CircuitState.HALF_OPEN &&
      this.successCount >= this.config.halfOpenMaxAttempts
    ) {
      logger.warn("Circuit breaker HALF_OPEN max attempts reached");
      return undefined;
    }

    // Execute function
    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure(error);
      throw error; // Re-throw to caller
    }
  }

  /**
   * Handle successful execution.
   */
  private onSuccess(): void {
    if (this.state === CircuitState.HALF_OPEN) {
      this.successCount++;
      logger.info(
        { success_count: this.successCount },
        "Circuit breaker HALF_OPEN success"
      );

      // Transition to CLOSED after successful test
      if (this.successCount >= this.config.halfOpenMaxAttempts) {
        logger.info("Circuit breaker closing (recovered)");
        this.state = CircuitState.CLOSED;
        this.failureCount = 0;
        this.successCount = 0;
      }
    } else if (this.state === CircuitState.CLOSED) {
      // Reset failure count on success
      if (this.failureCount > 0) {
        logger.debug("Circuit breaker resetting failure count");
        this.failureCount = 0;
      }
    }
  }

  /**
   * Handle failed execution.
   */
  private onFailure(error: unknown): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    logger.warn(
      {
        state: this.state,
        failure_count: this.failureCount,
        threshold: this.config.threshold,
        error: error instanceof Error ? error.message : String(error),
      },
      "Circuit breaker recorded failure"
    );

    if (this.state === CircuitState.HALF_OPEN) {
      // Failed in HALF_OPEN, go back to OPEN
      logger.warn("Circuit breaker failed in HALF_OPEN, reopening");
      this.state = CircuitState.OPEN;
      this.successCount = 0;
    } else if (
      this.state === CircuitState.CLOSED &&
      this.failureCount >= this.config.threshold
    ) {
      // Too many failures, open circuit
      logger.error(
        {
          failure_count: this.failureCount,
          threshold: this.config.threshold,
        },
        "Circuit breaker opening due to failures"
      );
      this.state = CircuitState.OPEN;
    }
  }

  /**
   * Manually reset circuit breaker.
   */
  public reset(): void {
    logger.info("Circuit breaker manually reset");
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    this.lastFailureTime = 0;
  }

  /**
   * Check if circuit is open.
   */
  public isOpen(): boolean {
    return this.state === CircuitState.OPEN;
  }
}
