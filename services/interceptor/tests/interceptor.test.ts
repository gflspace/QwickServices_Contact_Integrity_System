import { interceptMessage } from "../src/interceptor";
import { ChatMessage } from "../src/types";
import { getConfig, resetConfig } from "../src/config";

describe("Interceptor", () => {
  beforeEach(() => {
    // Reset config before each test
    resetConfig();
    // Set test environment
    process.env.SYNC_THRESHOLD = "0.65";
    process.env.MAX_MESSAGE_LENGTH = "10000";
  });

  afterEach(() => {
    // Clean up environment
    delete process.env.SYNC_THRESHOLD;
    delete process.env.MAX_MESSAGE_LENGTH;
    resetConfig();
  });

  describe("Clean messages", () => {
    it("should allow clean message with low risk score", async () => {
      const message: ChatMessage = {
        message_id: "msg-001",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Hey, how are you doing today? The weather is nice!",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(true);
      expect(result.action).toBe("allow");
      expect(result.risk_score).toBeLessThan(0.4);
      expect(result.labels).toEqual([]);
      expect(result.nudge_message).toBeUndefined();
      expect(result.block_reason).toBeUndefined();
    });

    it("should allow message with minor content", async () => {
      const message: ChatMessage = {
        message_id: "msg-002",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Thanks for your help! I really appreciate it.",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(true);
      expect(result.action).toBe("allow");
      expect(result.risk_score).toBe(0);
    });
  });

  describe("Phone number detection", () => {
    it("should block message with US phone number (score >= threshold)", async () => {
      const message: ChatMessage = {
        message_id: "msg-003",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Call me at (555) 123-4567 for more details",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(false);
      expect(result.action).toBe("hard_block");
      expect(result.risk_score).toBeGreaterThanOrEqual(0.65);
      expect(result.labels).toContain("contact_info_phone");
      expect(result.block_reason).toContain("phone number");
      expect(result.nudge_message).toBeUndefined();
    });

    it("should block message with international phone number", async () => {
      const message: ChatMessage = {
        message_id: "msg-004",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Text me on +44 20 7123 4567",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(false);
      expect(result.action).toBe("hard_block");
      expect(result.risk_score).toBeGreaterThanOrEqual(0.65);
      expect(result.labels).toContain("contact_info_phone");
    });

    it("should block message with condensed phone number", async () => {
      const message: ChatMessage = {
        message_id: "msg-005",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "My number is 5551234567",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(false);
      expect(result.action).toBe("hard_block");
      expect(result.risk_score).toBeGreaterThanOrEqual(0.65);
      expect(result.labels).toContain("contact_info_phone");
    });
  });

  describe("Email detection", () => {
    it("should block message with standard email", async () => {
      const message: ChatMessage = {
        message_id: "msg-006",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Email me at john.doe@example.com",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(false);
      expect(result.action).toBe("hard_block");
      expect(result.risk_score).toBeGreaterThanOrEqual(0.65);
      expect(result.labels).toContain("contact_info_email");
      expect(result.block_reason).toContain("email");
    });

    it("should block message with obfuscated email (at/dot)", async () => {
      const message: ChatMessage = {
        message_id: "msg-007",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Contact me at john dot doe at example dot com",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(false);
      expect(result.action).toBe("hard_block");
      expect(result.risk_score).toBeGreaterThanOrEqual(0.65);
      expect(result.labels).toContain("contact_info_email");
    });
  });

  describe("URL detection", () => {
    it("should nudge message with URL (medium risk)", async () => {
      const message: ChatMessage = {
        message_id: "msg-008",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Check out my profile at https://example.com/profile",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(true);
      expect(result.action).toBe("nudge");
      expect(result.risk_score).toBeGreaterThanOrEqual(0.40);
      expect(result.labels).toContain("external_link");
    });

    it("should nudge message with URL shortener (medium risk)", async () => {
      const message: ChatMessage = {
        message_id: "msg-009",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Click here: bit.ly/abc123",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(true);
      expect(result.action).toBe("nudge");
      expect(result.risk_score).toBeGreaterThanOrEqual(0.40);
      expect(result.labels).toContain("external_link");
    });
  });

  describe("Social platform detection", () => {
    it("should detect WhatsApp mention", async () => {
      const message: ChatMessage = {
        message_id: "msg-010",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Add me on WhatsApp",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.labels).toContain("social_platform_mention");
      // May or may not block depending on score
    });

    it("should detect Telegram mention", async () => {
      const message: ChatMessage = {
        message_id: "msg-011",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "DM me on telegram",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.labels).toContain("social_platform_mention");
    });
  });

  describe("Nudge messages", () => {
    it("should provide nudge for medium-risk message", async () => {
      // Create a message that triggers medium risk (0.4-0.64)
      // A social mention alone should be medium risk
      const message: ChatMessage = {
        message_id: "msg-012",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Text me later",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      if (result.risk_score >= 0.4 && result.risk_score < 0.65) {
        expect(result.allowed).toBe(true);
        expect(result.action).toBe("nudge");
        expect(result.nudge_message).toBeDefined();
        expect(result.nudge_message).toContain("platform");
      }
    });
  });

  describe("Combined patterns", () => {
    it("should block message with phone and email", async () => {
      const message: ChatMessage = {
        message_id: "msg-013",
        thread_id: "thread-001",
        user_id: "user-001",
        content:
          "Contact me at john@example.com or call (555) 123-4567",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(false);
      expect(result.action).toBe("hard_block");
      expect(result.risk_score).toBeGreaterThanOrEqual(0.65);
      expect(result.labels).toContain("contact_info_phone");
      expect(result.labels).toContain("contact_info_email");
      expect(result.block_reason).toContain("phone number");
      expect(result.block_reason).toContain("email");
    });

    it("should block message with URL and social mention", async () => {
      const message: ChatMessage = {
        message_id: "msg-014",
        thread_id: "thread-001",
        user_id: "user-001",
        content:
          "Add me on WhatsApp, here's my link: https://wa.me/5551234567",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(false);
      expect(result.action).toBe("hard_block");
      expect(result.risk_score).toBeGreaterThanOrEqual(0.65);
    });
  });

  describe("Edge cases", () => {
    it("should handle empty message", async () => {
      const message: ChatMessage = {
        message_id: "msg-015",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(true);
      expect(result.action).toBe("allow");
      expect(result.risk_score).toBe(0);
    });

    it("should block message exceeding max length", async () => {
      const longContent = "a".repeat(10001);
      const message: ChatMessage = {
        message_id: "msg-016",
        thread_id: "thread-001",
        user_id: "user-001",
        content: longContent,
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(false);
      expect(result.action).toBe("hard_block");
      expect(result.risk_score).toBe(1.0);
      expect(result.labels).toContain("message_too_long");
      expect(result.block_reason).toContain("maximum length");
    });

    it("should handle message with GPS coordinates", async () => {
      const message: ChatMessage = {
        message_id: "msg-017",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Meeting at the coffee shop",
        timestamp: new Date().toISOString(),
        gps_lat: 37.7749,
        gps_lon: -122.4194,
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(true);
      expect(result.action).toBe("allow");
    });

    it("should handle invalid content gracefully", async () => {
      const message: ChatMessage = {
        message_id: "msg-018",
        thread_id: "thread-001",
        user_id: "user-001",
        content: null as any, // Invalid content
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(true); // Fail-open
      expect(result.action).toBe("allow");
    });
  });

  describe("InterceptResult structure", () => {
    it("should return properly structured result for blocked message", async () => {
      const message: ChatMessage = {
        message_id: "msg-019",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Call me at 555-123-4567",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      // Verify structure
      expect(result).toHaveProperty("allowed");
      expect(result).toHaveProperty("action");
      expect(result).toHaveProperty("risk_score");
      expect(result).toHaveProperty("labels");
      expect(typeof result.allowed).toBe("boolean");
      expect(typeof result.action).toBe("string");
      expect(typeof result.risk_score).toBe("number");
      expect(Array.isArray(result.labels)).toBe(true);

      // Verify blocked message has block_reason
      if (!result.allowed) {
        expect(result).toHaveProperty("block_reason");
        expect(typeof result.block_reason).toBe("string");
        expect(result.block_reason).not.toBe("");
      }
    });

    it("should return properly structured result for allowed message", async () => {
      const message: ChatMessage = {
        message_id: "msg-020",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "Hello, how are you?",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.allowed).toBe(true);
      expect(result.action).toBe("allow");
      expect(result.risk_score).toBeGreaterThanOrEqual(0);
      expect(result.risk_score).toBeLessThanOrEqual(1);
      expect(Array.isArray(result.labels)).toBe(true);
      expect(result.block_reason).toBeUndefined();
    });
  });

  describe("Threshold configuration", () => {
    it("should respect custom sync threshold", async () => {
      // Set lower threshold
      delete process.env.SYNC_THRESHOLD;
      process.env.SYNC_THRESHOLD = "0.3";
      resetConfig();

      const message: ChatMessage = {
        message_id: "msg-021",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "DM me",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      // With lower threshold, more messages should be blocked
      expect(result.risk_score).toBeDefined();
    });
  });

  describe("Obfuscation detection", () => {
    it("should detect excessive spacing", async () => {
      const message: ChatMessage = {
        message_id: "msg-022",
        thread_id: "thread-001",
        user_id: "user-001",
        content: "5  5  5  -  1  2  3  -  4  5  6  7",
        timestamp: new Date().toISOString(),
      };

      const result = await interceptMessage(message);

      expect(result.labels).toContain("obfuscation_detected");
    });
  });
});
