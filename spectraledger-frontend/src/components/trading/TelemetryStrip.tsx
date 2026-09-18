"use client";

import { motion } from "framer-motion";
import { Card, CardHeader } from "@/components/ui/Card";
import { useMarketStore } from "@/store/useMarketStore";
import { fmtMbps } from "@/lib/format";
import { cn } from "@/lib/cn";

export function TelemetryStrip() {
  const fleet = useMarketStore((s) => s.fleet);
  const telemetry = useMarketStore((s) => s.telemetry);

  return (
    <Card>
      <CardHeader title="Live slice telemetry" subtitle="Throughput & latency across the seven-company fleet, ~2s cadence" />
      <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
        {fleet.length === 0
          ? [...Array(7)].map((_, i) => <div key={i} className="h-24 rounded-xl skeleton" />)
          : fleet.map((s) => {
              const t = telemetry[s.slice_id];
              const capacity = s.capacity_mbps;
              const util = t ? t.throughput_mbps / capacity : s.base_utilization_pct;
              const isBuyer = s.slice_id === "slice-factory-09";
              return (
                <div key={s.slice_id} className="rounded-xl border border-border bg-surface-2/60 p-3">
                  <p className="truncate font-mono text-[11px] font-semibold">{s.slice_id.replace("slice-", "")}</p>
                  <p className="mb-2 text-[10px] text-muted">{s.slice_type}</p>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
                    <motion.div
                      className={cn("h-full rounded-full", isBuyer ? "bg-warning" : util > 0.85 ? "bg-danger" : "bg-accent")}
                      animate={{ width: `${Math.min(100, util * 100)}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-muted">
                    <span>{t ? fmtMbps(t.throughput_mbps, 0) : "—"}</span>
                    <span>{t ? `${t.latency_ms.toFixed(1)}ms` : "—"}</span>
                  </div>
                </div>
              );
            })}
      </div>
    </Card>
  );
}
