"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Bot, CheckCircle2, Clock, XCircle } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useMarketStore } from "@/store/useMarketStore";
import { fmtMbps, fmtTime, fmtUsdMicro, shortId } from "@/lib/format";
import { cn } from "@/lib/cn";

export function TradeTape() {
  const trades = useMarketStore((s) => s.trades);

  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Trade tape" subtitle="Live market-wide fills, newest first" />
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {trades.length === 0 ? (
          <div className="space-y-2 p-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-10 w-full rounded skeleton" />
            ))}
          </div>
        ) : (
          <ul className="space-y-1">
            <AnimatePresence initial={false}>
              {trades.map((t) => (
                <motion.li
                  key={t.id}
                  layout
                  initial={{ opacity: 0, y: -14 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ type: "spring", damping: 24, stiffness: 220 }}
                  className="flash-row flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-xs hover:bg-white/[0.03]"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    {t.isAgentTrade ? (
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-2/15 text-accent-2" title="Placed autonomously by an AI agent">
                        <Bot size={12} />
                      </span>
                    ) : (
                      <span className="h-5 w-5 shrink-0 rounded-full bg-white/5" />
                    )}
                    <div className="min-w-0">
                      <p className="truncate font-mono">
                        <span className="text-accent">{shortId(t.sellerTenantId || `seller-${t.id}`, 6)}</span>
                        <span className="text-muted"> → </span>
                        <span className="text-warning">{shortId(t.buyerTenantId || `buyer-${t.id}`, 6)}</span>
                      </p>
                      <p className="text-[10px] text-muted">{fmtTime(t.clearedAt)} · {t.qosTier}</p>
                    </div>
                  </div>
                  <div className="text-right font-mono">
                    <p>{fmtMbps(t.quantityMbps, 0)}</p>
                    <p className="text-[10px] text-muted">{fmtUsdMicro(t.executionPrice)}</p>
                  </div>
                  <ReassignBadge status={t.sliceReassignmentStatus} />
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </div>
    </Card>
  );
}

function ReassignBadge({ status }: { status: "PENDING" | "CONFIRMED" | "FAILED" }) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={status}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        transition={{ duration: 0.25 }}
      >
        <Badge
          tone={status === "CONFIRMED" ? "success" : status === "FAILED" ? "danger" : "warning"}
          className={cn(status === "PENDING" && "pulse-dot")}
        >
          {status === "PENDING" && <Clock size={10} />}
          {status === "CONFIRMED" && <CheckCircle2 size={10} />}
          {status === "FAILED" && <XCircle size={10} />}
          {status}
        </Badge>
      </motion.div>
    </AnimatePresence>
  );
}
