"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowDownCircle, ArrowUpCircle, Lock, ShieldCheck } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useAgentStore } from "@/store/useAgentStore";
import { fmtMbps, fmtTime, fmtUsdMicro } from "@/lib/format";
import { cn } from "@/lib/cn";

const DECISION_STYLE = {
  buy: { icon: ArrowDownCircle, tone: "accent" as const },
  sell: { icon: ArrowUpCircle, tone: "danger" as const },
  list: { icon: ArrowUpCircle, tone: "accent2" as const },
  hold: { icon: Lock, tone: "neutral" as const },
};

export function ReasoningFeed() {
  const reasoning = useAgentStore((s) => s.reasoning);

  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Live agent reasoning" subtitle="Straight from every agent.decision event — no summarization" />
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {reasoning.length === 0 ? (
          [...Array(4)].map((_, i) => <div key={i} className="h-20 w-full rounded-xl skeleton" />)
        ) : (
          <AnimatePresence initial={false}>
            {reasoning.map((r, i) => {
              const style = DECISION_STYLE[r.decision];
              const Icon = style.icon;
              return (
                <motion.div
                  key={`${r.slice_id}-${r.decided_at}-${i}`}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3 }}
                  className="rounded-xl border border-border bg-surface-2/60 p-3"
                >
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Icon size={14} className={cn(style.tone === "accent" && "text-accent", style.tone === "danger" && "text-danger", style.tone === "accent2" && "text-accent-2", style.tone === "neutral" && "text-muted")} />
                      <span className="font-mono text-xs font-semibold">{r.slice_id}</span>
                      <Badge tone={style.tone}>{r.role} · {r.decision}</Badge>
                    </div>
                    <span className="font-mono text-[10px] text-muted">{fmtTime(r.decided_at)}</span>
                  </div>
                  <p className="text-xs leading-relaxed text-foreground/75">{r.reasoning}</p>
                  <div className="mt-2 flex items-center gap-3 text-[10px] font-mono text-muted">
                    {r.quantity_mbps > 0 && <span>{fmtMbps(r.quantity_mbps, 0)}</span>}
                    {r.price > 0 && <span>{fmtUsdMicro(r.price)}</span>}
                    <span className={cn("flex items-center gap-1", r.sla_gate_passed ? "text-success" : "text-danger")}>
                      <ShieldCheck size={11} /> SLA gate {r.sla_gate_passed ? "passed" : "blocked"}
                    </span>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </Card>
  );
}
