"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Card, CardHeader } from "@/components/ui/Card";
import { useMarketStore } from "@/store/useMarketStore";
import { fmtMbps, fmtUsdMicro } from "@/lib/format";
import { cn } from "@/lib/cn";

export function OrderBookDepth() {
  const orderBook = useMarketStore((s) => s.orderBook);
  const [idx, setIdx] = useState(0);

  const buckets = orderBook.filter((b) => b.bids.length || b.asks.length);
  const bucket = buckets[Math.min(idx, Math.max(0, buckets.length - 1))];

  const maxQty = bucket
    ? Math.max(1, ...bucket.bids.map((b) => b.totalQuantityMbps), ...bucket.asks.map((a) => a.totalQuantityMbps))
    : 1;

  return (
    <Card>
      <CardHeader
        title="Live order book"
        subtitle={bucket ? `${bucket.qosTier} · ${bucket.durationMinutes}-min window` : "Waiting for resting orders…"}
        right={
          buckets.length > 1 && (
            <div className="flex gap-1">
              {buckets.map((b, i) => (
                <button
                  key={`${b.qosTier}-${b.durationMinutes}`}
                  onClick={() => setIdx(i)}
                  className={cn(
                    "rounded-md border px-2 py-1 text-[10px] font-mono uppercase",
                    i === idx ? "border-accent/50 text-accent bg-accent/10" : "border-border text-muted hover:text-foreground"
                  )}
                >
                  {b.qosTier}
                </button>
              ))}
            </div>
          )
        }
      />
      {!bucket ? (
        <div className="grid grid-cols-2 gap-4 p-5">
          {[0, 1].map((c) => (
            <div key={c} className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-6 w-full rounded skeleton" />
              ))}
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 divide-x divide-border">
          <div className="p-3">
            <div className="mb-1.5 flex justify-between px-2 text-[10px] uppercase tracking-wide text-muted">
              <span>Bid (USD/Mbps-min)</span>
              <span>Mbps</span>
            </div>
            <div className="space-y-1">
              {bucket.bids.slice(0, 8).map((b, i) => (
                <Row key={i} price={b.price} qty={b.totalQuantityMbps} max={maxQty} side="bid" />
              ))}
              {bucket.bids.length === 0 && <EmptySide label="No resting bids" />}
            </div>
          </div>
          <div className="p-3">
            <div className="mb-1.5 flex justify-between px-2 text-[10px] uppercase tracking-wide text-muted">
              <span>Mbps</span>
              <span>Ask (USD/Mbps-min)</span>
            </div>
            <div className="space-y-1">
              {bucket.asks.slice(0, 8).map((a, i) => (
                <Row key={i} price={a.price} qty={a.totalQuantityMbps} max={maxQty} side="ask" />
              ))}
              {bucket.asks.length === 0 && <EmptySide label="No resting asks" />}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

function Row({ price, qty, max, side }: { price: number; qty: number; max: number; side: "bid" | "ask" }) {
  const pct = Math.max(4, Math.round((qty / max) * 100));
  const isBid = side === "bid";
  return (
    <div className="relative flex h-6 items-center overflow-hidden rounded px-2 text-xs font-mono">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ type: "spring", damping: 22, stiffness: 140 }}
        className={cn("absolute inset-y-0", isBid ? "right-0 bg-accent/15" : "left-0 bg-danger/15")}
      />
      <div className={cn("relative z-10 flex w-full", isBid ? "flex-row-reverse justify-between" : "justify-between")}>
        <span className={isBid ? "text-accent" : "text-danger"}>{fmtUsdMicro(price)}</span>
        <span className="text-foreground/70">{fmtMbps(qty, 0)}</span>
      </div>
    </div>
  );
}

function EmptySide({ label }: { label: string }) {
  return <p className="px-2 py-3 text-xs text-muted">{label}</p>;
}
