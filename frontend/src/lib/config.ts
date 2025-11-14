/**
 * Application configuration
 * Reads from environment variables with fallbacks
 */

export const config = {
  api: {
    baseUrl:
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    timeout: 30000,
  },
  app: {
    name: "CareerPilot",
    version: "0.1.0",
  },
} as const;

export const API_BASE = config.api.baseUrl;

