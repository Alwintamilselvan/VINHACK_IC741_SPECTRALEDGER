"use client";

import { useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { aiApi } from "@/lib/api/aiClient";
import { demoEngine } from "@/lib/demo/engine";
import { useConnStore } from "@/store/useConnStore";
import { useMarketStore } from "@/store/useMarketStore";
import { useCountUp } from "@/hooks/useCountUp";
import { fmtCompact, fmtUsd } from "@/lib/format";
import type { RevenueSummary } from "@/lib/types";

export function RevenueTicker() {
  const ai = useConnStore((s) => s.ai);
  const trades = useMarketStore((s) => s.trades);
  const [revenue, setRevenue] = useState<RevenueSummary>({ trade_count: 0, total_notional_volume: 0, total_fees_collected: 0 });

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      try {
        const r = ai === "live" ? await aiApi.revenue() : demoEngine.getRevenue();
        if (!cancelled) setRevenue(r);
      } catch {
        if (!cancelled) setRevenue(demoEngine.getRevenue());
      }
    }
    refresh();
    const t = setInterval(refresh, 2500);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
    // re-poll whenever a new trade lands, for snappier feel on top of the interval
  }, [ai, trades.length]);

  const animatedFees = useCountUp(revenue.total_fees_collected);

  return (
    <Card className="flex items-center gap-4 p-4">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-success/10 text-success">
        <TrendingUp size={18} />
      </div>
      <div className="flex-1">
        <p className="text-[10px] uppercase tracking-wide text-muted">Platform revenue (2% fee)</p>
        <p className="font-mono text-xl font-bold text-success">{fmtUsd(animatedFees)}</p>
      </div>
      <div className="text-right">
        <p className="font-mono text-sm">{revenue.trade_count}</p>
        <p className="text-[10px] text-muted">trades cleared</p>
      </div>
      <div className="text-right">
        <p className="font-mono text-sm">${fmtCompact(revenue.total_notional_volume)}</p>
        <p className="text-[10px] text-muted">notional volume</p>
      </div>
    </Card>
  );
}
