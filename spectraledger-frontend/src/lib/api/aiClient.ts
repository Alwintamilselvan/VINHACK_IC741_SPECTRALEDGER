import { AI_API_URL } from "@/lib/config";
import type {
  AgentDecisionEvent,
  DemoSlice,
  ForecastResponse,
  PriceResponse,
  RevenueSummary,
  RevenueTrade,
} from "@/lib/types";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${AI_API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`AI engine request failed (${res.status}) on ${path}`);
  return res.json() as Promise<T>;
}

export const aiApi = {
  forecast: (payload: { slice_id: string; horizon_minutes?: number; telemetry?: unknown }) =>
    request<ForecastResponse>("/forecast", { method: "POST", body: JSON.stringify(payload) }),
  price: (payload: { slice_id: string; qos_tier?: string }) =>
    request<PriceResponse>("/price", { method: "POST", body: JSON.stringify(payload) }),
  agentEvaluate: (payload: { slice_id: string; role: "buyer" | "seller" }) =>
    request<AgentDecisionEvent>("/agent/evaluate", { method: "POST", body: JSON.stringify(payload) }),
  revenue: () => request<RevenueSummary>("/revenue"),
  revenueTrades: () => request<RevenueTrade[]>("/revenue/trades"),
  demoSlices: () => request<DemoSlice[]>("/demo/slices"),
  demoTelemetry: (sliceId: string) => request<unknown>(`/demo/telemetry/${sliceId}`),
  /** polling fallback for the same 3 topics the WebSocket carries */
  events: (topic: "telemetry.raw" | "agent.decision" | "trade.executed") =>
    request<unknown[]>(`/events/${topic}`),
  /** lightweight reachability probe */
  ping: (signal?: AbortSignal) => request<DemoSlice[]>("/demo/slices", { signal }),
};
