// Central place for the two backend base URLs. Both services are reached
// directly from the browser — see README "Architecture decision" for why:
// the Java backend has no relay for AI-engine-only data (telemetry, forecasts,
// pricing explanations, agent reasoning), so the frontend is a client of both.

export const JAVA_API_URL =
  process.env.NEXT_PUBLIC_JAVA_API_URL?.replace(/\/$/, "") || "http://localhost:8080";

export const JAVA_WS_URL = `${JAVA_API_URL}/ws`;

export const AI_API_URL =
  process.env.NEXT_PUBLIC_AI_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export const AI_WS_URL = AI_API_URL.replace(/^http/, "ws") + "/ws/stream";

/** How long a live connection attempt gets before we fall back to demo mode. */
export const CONNECT_TIMEOUT_MS = 4000;

export const PLATFORM_FEE_PCT = 0.02;

export const QOS_TIERS = ["BRONZE", "SILVER", "GOLD", "PLATINUM"] as const;

export const SEEDED_LOGINS = [
  { username: "vertex", label: "Vertex Logistics" },
  { username: "aurora", label: "Aurora Manufacturing" },
  { username: "helios", label: "Helios Cloud" },
  { username: "nimbus", label: "Nimbus Retail" },
] as const;

export const ADMIN_LOGIN = { username: "admin", label: "Platform Admin" };
