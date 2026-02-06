import { ChatMessage, InterceptResult } from "./types";
import { getConfig } from "./config";
import pino from "pino";

const logger = pino({ name: "interceptor" });

/**
 * Pattern definitions for Stage 1 fast detection.
 * These patterns are optimized for speed while maintaining accuracy.
 */
const PATTERNS = {
  // Phone number patterns: international and US formats
  phone: [
    // International format with various separators
    /(?:\+|00)\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}/g,
    // US format: (123) 456-7890, 123-456-7890, 123.456.7890
    /\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/g,
    // Condensed: 1234567890 (10+ digits)
    /\b\d{10,15}\b/g,
  ],

  // Email patterns: standard and obfuscated
  email: [
    // Standard email
    /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
    // Obfuscated: "at" instead of @
    /[a-zA-Z0-9._%+-]+\s*\(?at\)?\s*[a-zA-Z0-9.-]+\s*\(?dot\)?\s*[a-zA-Z]{2,}/gi,
    // Spaced out: j o h n @ e x a m p l e . c o m
    /\b[a-z]\s+[a-z]\s+[a-z].*@.*[a-z]\s+[a-z]\s+[a-z]\b/gi,
  ],

  // URL patterns: protocols and shorteners
  url: [
    // Standard URLs with protocol
    /https?:\/\/[^\s]+/gi,
    // URLs without protocol
    /(?:www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/gi,
    // Common shorteners
    /\b(?:bit\.ly|tinyurl\.com|goo\.gl|t\.co|short\.link)\/[a-zA-Z0-9]+/gi,
  ],

  // Social media keywords
  social: [
    /\b(?:whatsapp|telegram|snapchat|snap|insta|instagram|discord|kik|signal)\b/gi,
    /\bDM\s+me\b/gi,
    /\btext\s+me\b/gi,
    /\bcontact\s+(?:me|us)\s+(?:at|on)\b/gi,
  ],

  // Obfuscation techniques
  obfuscation: [
    // Excessive spacing
    /[a-zA-Z0-9]\s{2,}[a-zA-Z0-9]/g,
    // Character substitution hints: @ as (at), . as (dot)
    /\b\w+\s*\(at\)\s*\w+\s*\(dot\)\s*\w+\b/gi,
    // Numbers spelled out
    /\b(?:zero|one|two|three|four|five|six|seven|eight|nine)\b/gi,
  ],
};

/**
 * Weight configuration for scoring.
 * These weights determine how much each pattern type contributes to risk score.
 */
const PATTERN_WEIGHTS = {
  phone: 0.85,
  email: 0.80,
  url: 0.50,
  social: 0.40,
  obfuscation: 0.15,
};

interface PatternMatch {
  type: "phone" | "email" | "url" | "social" | "obfuscation";
  count: number;
  samples: string[];
}

/**
 * Scan message content for patterns and return matches.
 * This is the core of the Stage 1 inline detection.
 */
function scanPatterns(content: string): PatternMatch[] {
  const matches: PatternMatch[] = [];

  // Phone detection
  const phoneMatches = new Set<string>();
  PATTERNS.phone.forEach((regex) => {
    const found = content.match(regex);
    if (found) {
      found.forEach((match) => phoneMatches.add(match.trim()));
    }
  });
  if (phoneMatches.size > 0) {
    matches.push({
      type: "phone",
      count: phoneMatches.size,
      samples: Array.from(phoneMatches).slice(0, 3),
    });
  }

  // Email detection
  const emailMatches = new Set<string>();
  PATTERNS.email.forEach((regex) => {
    const found = content.match(regex);
    if (found) {
      found.forEach((match) => emailMatches.add(match.trim()));
    }
  });
  if (emailMatches.size > 0) {
    matches.push({
      type: "email",
      count: emailMatches.size,
      samples: Array.from(emailMatches).slice(0, 3),
    });
  }

  // URL detection
  const urlMatches = new Set<string>();
  PATTERNS.url.forEach((regex) => {
    const found = content.match(regex);
    if (found) {
      found.forEach((match) => urlMatches.add(match.trim()));
    }
  });
  if (urlMatches.size > 0) {
    matches.push({
      type: "url",
      count: urlMatches.size,
      samples: Array.from(urlMatches).slice(0, 3),
    });
  }

  // Social media keyword detection
  const socialMatches = new Set<string>();
  PATTERNS.social.forEach((regex) => {
    const found = content.match(regex);
    if (found) {
      found.forEach((match) => socialMatches.add(match.trim()));
    }
  });
  if (socialMatches.size > 0) {
    matches.push({
      type: "social",
      count: socialMatches.size,
      samples: Array.from(socialMatches).slice(0, 3),
    });
  }

  // Obfuscation detection
  const obfuscationMatches = new Set<string>();
  PATTERNS.obfuscation.forEach((regex) => {
    const found = content.match(regex);
    if (found) {
      found.forEach((match) => obfuscationMatches.add(match.trim()));
    }
  });
  if (obfuscationMatches.size > 0) {
    matches.push({
      type: "obfuscation",
      count: obfuscationMatches.size,
      samples: Array.from(obfuscationMatches).slice(0, 3),
    });
  }

  return matches;
}

/**
 * Calculate risk score based on pattern matches.
 * Score is normalized to 0.0-1.0 range.
 */
function calculateRiskScore(matches: PatternMatch[]): number {
  if (matches.length === 0) return 0.0;

  // Base score: highest weight among detected patterns
  let maxWeight = 0.0;
  let totalContribution = 0.0;

  matches.forEach((match) => {
    const weight = PATTERN_WEIGHTS[match.type] || 0.1;
    maxWeight = Math.max(maxWeight, weight);
    // Additional matches of same type add smaller increments
    const contribution = weight * Math.min(match.count, 3) / 3;
    totalContribution += contribution;
  });

  // Score is primarily driven by the highest-weight pattern detected
  // Multi-type boost: detecting multiple types increases score
  const multiTypeBoost = matches.length > 1 ? 0.10 * (matches.length - 1) : 0;
  const score = Math.max(maxWeight * 0.85, totalContribution * 0.7) + multiTypeBoost;

  // Cap at 1.0
  return Math.min(score, 1.0);
}

/**
 * Generate labels based on pattern matches.
 */
function generateLabels(matches: PatternMatch[]): string[] {
  const labels: string[] = [];

  matches.forEach((match) => {
    switch (match.type) {
      case "phone":
        labels.push("contact_info_phone");
        break;
      case "email":
        labels.push("contact_info_email");
        break;
      case "url":
        labels.push("external_link");
        break;
      case "social":
        labels.push("social_platform_mention");
        break;
      case "obfuscation":
        labels.push("obfuscation_detected");
        break;
    }
  });

  return labels;
}

/**
 * Generate appropriate nudge message based on risk level and detected patterns.
 */
function generateNudgeMessage(
  riskScore: number,
  matches: PatternMatch[]
): string | undefined {
  // Only generate nudges for medium risk (0.4-0.64)
  if (riskScore < 0.4 || riskScore >= 0.65) {
    return undefined;
  }

  const hasPhone = matches.some((m) => m.type === "phone");
  const hasEmail = matches.some((m) => m.type === "email");
  const hasSocial = matches.some((m) => m.type === "social");

  if (hasPhone || hasEmail) {
    return "Sharing personal contact information may violate platform policies and put you at risk. Please keep conversations on the platform.";
  }

  if (hasSocial) {
    return "We noticed you're trying to move the conversation off-platform. For your safety, please continue chatting here.";
  }

  return "This message may contain content that violates our community guidelines. Please review before sending.";
}

/**
 * Generate block reason for high-risk messages.
 */
function generateBlockReason(matches: PatternMatch[]): string {
  const types = matches.map((m) => m.type);
  const reasons: string[] = [];

  if (types.includes("phone")) {
    reasons.push("phone number");
  }
  if (types.includes("email")) {
    reasons.push("email address");
  }
  if (types.includes("url")) {
    reasons.push("external link");
  }
  if (types.includes("social")) {
    reasons.push("social media reference");
  }

  if (reasons.length === 0) {
    return "Message blocked due to potential policy violation";
  }

  return `Message blocked: detected ${reasons.join(", ")}. Keep conversations on the platform for your safety.`;
}

/**
 * Main interceptor function.
 * Performs inline Stage 1 analysis and makes synchronous blocking decision.
 *
 * @param message - The chat message to intercept
 * @returns InterceptResult with blocking decision and metadata
 */
export async function interceptMessage(
  message: ChatMessage
): Promise<InterceptResult> {
  const startTime = Date.now();
  const config = getConfig();

  try {
    // Validate message content
    if (!message.content || typeof message.content !== "string") {
      logger.warn(
        { message_id: message.message_id },
        "Invalid message content"
      );
      return {
        allowed: true,
        action: "allow",
        risk_score: 0.0,
        labels: [],
      };
    }

    // Check message length
    if (message.content.length > config.max_message_length) {
      logger.warn(
        {
          message_id: message.message_id,
          length: message.content.length,
        },
        "Message exceeds maximum length"
      );
      return {
        allowed: false,
        action: "hard_block",
        risk_score: 1.0,
        labels: ["message_too_long"],
        block_reason: `Message exceeds maximum length of ${config.max_message_length} characters`,
      };
    }

    // Scan for patterns
    const matches = scanPatterns(message.content);

    // Calculate risk score
    const riskScore = calculateRiskScore(matches);

    // Generate labels
    const labels = generateLabels(matches);

    const processingMs = Date.now() - startTime;

    // Decision logic based on sync threshold
    if (riskScore >= config.sync_threshold) {
      // High risk: block synchronously
      const blockReason = generateBlockReason(matches);

      logger.info(
        {
          message_id: message.message_id,
          risk_score: riskScore,
          labels,
          processing_ms: processingMs,
        },
        "Message blocked (sync)"
      );

      return {
        allowed: false,
        action: "hard_block",
        risk_score: riskScore,
        labels,
        block_reason: blockReason,
      };
    } else if (riskScore >= 0.4) {
      // Medium risk: allow with nudge
      const nudgeMessage = generateNudgeMessage(riskScore, matches);

      logger.info(
        {
          message_id: message.message_id,
          risk_score: riskScore,
          labels,
          processing_ms: processingMs,
        },
        "Message allowed with nudge"
      );

      return {
        allowed: true,
        action: "nudge",
        risk_score: riskScore,
        labels,
        nudge_message: nudgeMessage,
      };
    } else {
      // Low risk: allow
      logger.debug(
        {
          message_id: message.message_id,
          risk_score: riskScore,
          processing_ms: processingMs,
        },
        "Message allowed (clean)"
      );

      return {
        allowed: true,
        action: "allow",
        risk_score: riskScore,
        labels: labels.length > 0 ? labels : [],
      };
    }
  } catch (error) {
    // Fail-open: if interceptor crashes, allow message
    logger.error(
      {
        message_id: message.message_id,
        error: error instanceof Error ? error.message : String(error),
      },
      "Interceptor error, failing open"
    );

    return {
      allowed: true,
      action: "allow",
      risk_score: 0.0,
      labels: ["interceptor_error"],
    };
  }
}
