"use client";

import { useMarketStore } from "@/store/useMarketStore";
import { fmtMbps, fmtUsdMicro, shortId } from "@/lib/format";
import { cn } from "@/lib/cn";

export function LiveTicker() {
  const trades = useMarketStore((s) => s.trades);
  const items = trades.length ? trades.slice(0, 14) : [];

  return (
    <div className="w-full overflow-hidden border-y border-border bg-surface/60 py-2.5">
      {items.length === 0 ? (
        <p className="text-center font-mono text-xs text-muted">Waiting for the first trade to clear…</p>
      ) : (
        <div className="flex w-max animate-marquee gap-8">
          {[...items, ...items].map((t, i) => (
            <span key={`${t.id}-${i}`} className="flex items-center gap-2 whitespace-nowrap font-mono text-xs text-foreground/70">
              <span className={cn("h-1.5 w-1.5 rounded-full", t.isAgentTrade ? "bg-accent-2" : "bg-accent")} />
              {shortId(t.sellerTenantId, 5)} → {shortId(t.buyerTenantId, 5)}
              <span className="text-accent">{fmtMbps(t.quantityMbps, 0)}</span>
              <span className="text-muted">@</span>
              <span>{fmtUsdMicro(t.executionPrice)}</span>
              <span className="text-border">/</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
