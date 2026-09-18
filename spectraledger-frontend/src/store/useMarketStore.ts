import { create } from "zustand";
import type { DemoSlice, OrderBookBucket, TelemetryRawEvent, Trade } from "@/lib/types";

interface MarketStore {
  fleet: DemoSlice[];
  telemetry: Record<string, TelemetryRawEvent>;
  orderBook: OrderBookBucket[];
  trades: Trade[];
  setFleet: (f: DemoSlice[]) => void;
  pushTelemetry: (e: TelemetryRawEvent) => void;
  setOrderBook: (b: OrderBookBucket[]) => void;
  upsertOrderBookBucket: (b: OrderBookBucket) => void;
  pushTrade: (t: Trade) => void;
}

export const useMarketStore = create<MarketStore>((set) => ({
  fleet: [],
  telemetry: {},
  orderBook: [],
  trades: [],
  setFleet: (fleet) => set({ fleet }),
  pushTelemetry: (e) => set((s) => ({ telemetry: { ...s.telemetry, [e.slice_id]: e } })),
  setOrderBook: (orderBook) => set({ orderBook }),
  upsertOrderBookBucket: (b) =>
    set((s) => {
      const idx = s.orderBook.findIndex((x) => x.qosTier === b.qosTier && x.durationMinutes === b.durationMinutes);
      const next = [...s.orderBook];
      if (idx >= 0) next[idx] = b;
      else next.push(b);
      return { orderBook: next };
    }),
  pushTrade: (t) =>
    set((s) => {
      const idx = s.trades.findIndex((x) => x.id === t.id);
      const next = [...s.trades];
      if (idx >= 0) next[idx] = { ...next[idx], ...t };
      else next.unshift(t);
      return { trades: next.slice(0, 60) };
    }),
}));
