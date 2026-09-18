"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Card, CardHeader } from "@/components/ui/Card";
import type { PriceComponents } from "@/lib/types";
import { fmtUsdMicro } from "@/lib/format";

function Factor({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-xl border border-border bg-surface-2 px-3 py-3 min-w-[84px]">
      <AnimatePresence mode="wait">
        <motion.span
          key={value.toFixed(3)}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.3 }}
          className="font-mono text-base font-semibold text-accent"
        >
          {value.toFixed(2)}×
        </motion.span>
      </AnimatePresence>
      <span className="text-center text-[10px] uppercase tracking-wide text-muted leading-tight">{label}</span>
    </div>
  );
}

export function PriceFormula({
  components,
  midPrice,
  explanation,
}: {
  components: PriceComponents;
  midPrice: number;
  explanation: string;
}) {
  return (
    <Card>
      <CardHeader title="The formula that shows its work" subtitle="Every price is fully explainable — nothing here is a black box" />
      <div className="p-5">
        <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3">
          <Factor label="Base rate" value={components.base_rate} />
          <span className="font-mono text-muted">×</span>
          <Factor label="Congestion" value={components.congestion_multiplier} />
          <span className="font-mono text-muted">×</span>
          <Factor label="QoS weight" value={components.qos_priority_weight} />
          <span className="font-mono text-muted">×</span>
          <Factor label="Urgency" value={components.urgency_factor} />
          <span className="font-mono text-muted">=</span>
          <div className="flex flex-col items-center gap-1 rounded-xl border border-accent/30 bg-accent/10 px-4 py-3 min-w-[110px]">
            <AnimatePresence mode="wait">
              <motion.span
                key={midPrice.toFixed(4)}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="font-mono text-base font-bold text-accent"
              >
                {fmtUsdMicro(midPrice)}
              </motion.span>
            </AnimatePresence>
            <span className="text-[10px] uppercase tracking-wide text-accent/70">Mid price / Mbps-hr</span>
          </div>
        </div>
        <p className="mt-4 text-xs leading-relaxed text-foreground/70">{explanation}</p>
      </div>
    </Card>
  );
}
