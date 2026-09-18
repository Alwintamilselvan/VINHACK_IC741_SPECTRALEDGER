"use client";

import { motion } from "framer-motion";
import { Lock, Unlock } from "lucide-react";
import { cn } from "@/lib/cn";

const SIZE = 108;
const STROKE = 9;
const R = (SIZE - STROKE) / 2;
const C = 2 * Math.PI * R;
const THRESHOLD = 0.5;

export function SLAGauge({ confidence, slaGatePassed }: { confidence: number; slaGatePassed: boolean }) {
  const pct = Math.max(0, Math.min(1, confidence));
  const offset = C * (1 - pct);
  const color = slaGatePassed ? "var(--success)" : "var(--danger)";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: SIZE, height: SIZE }}>
        <svg width={SIZE} height={SIZE} className="-rotate-90">
          <circle cx={SIZE / 2} cy={SIZE / 2} r={R} stroke="var(--border)" strokeWidth={STROKE} fill="none" />
          <motion.circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={R}
            stroke={color}
            strokeWidth={STROKE}
            strokeLinecap="round"
            fill="none"
            strokeDasharray={C}
            animate={{ strokeDashoffset: offset }}
            transition={{ type: "spring", damping: 20, stiffness: 90 }}
            style={{ filter: `drop-shadow(0 0 5px ${color})` }}
          />
          {/* threshold tick at 0.5 */}
          <line
            x1={SIZE / 2}
            y1={STROKE / 2}
            x2={SIZE / 2}
            y2={STROKE * 1.6}
            stroke="var(--warning)"
            strokeWidth={2}
            transform={`rotate(${THRESHOLD * 360} ${SIZE / 2} ${SIZE / 2})`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-lg font-bold">{Math.round(pct * 100)}%</span>
          <span className="text-[9px] uppercase text-muted">confidence</span>
        </div>
      </div>
      <div className={cn("flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-mono uppercase", slaGatePassed ? "border-success/30 text-success bg-success/10" : "border-danger/30 text-danger bg-danger/10")}>
        {slaGatePassed ? <Unlock size={11} /> : <Lock size={11} />}
        {slaGatePassed ? "SLA gate open" : "SLA gate locked"}
      </div>
    </div>
  );
}
