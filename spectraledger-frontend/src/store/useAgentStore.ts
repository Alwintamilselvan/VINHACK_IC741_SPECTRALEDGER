import { create } from "zustand";
import type { AgentDecisionEvent, ForecastResponse, PriceResponse } from "@/lib/types";

interface AgentStore {
  reasoning: AgentDecisionEvent[];
  forecasts: Record<string, ForecastResponse>;
  prices: Record<string, PriceResponse>;
  pushDecision: (e: AgentDecisionEvent) => void;
  setForecast: (sliceId: string, f: ForecastResponse) => void;
  setPrice: (sliceId: string, p: PriceResponse) => void;
}

export const useAgentStore = create<AgentStore>((set) => ({
  reasoning: [],
  forecasts: {},
  prices: {},
  pushDecision: (e) =>
    set((s) => ({ reasoning: [e, ...s.reasoning].slice(0, 80) })),
  setForecast: (sliceId, f) => set((s) => ({ forecasts: { ...s.forecasts, [sliceId]: f } })),
  setPrice: (sliceId, p) => set((s) => ({ prices: { ...s.prices, [sliceId]: p } })),
}));
