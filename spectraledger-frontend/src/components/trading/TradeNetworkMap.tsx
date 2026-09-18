"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Card, CardHeader } from "@/components/ui/Card";
import { useMarketStore } from "@/store/useMarketStore";
import { SEEDED_LOGINS } from "@/lib/config";
import { fmtMbps } from "@/lib/format";

const NODES = SEEDED_LOGINS.map((t, i) => ({
  id: `t-${t.username}`,
  label: t.label,
  // positioned on a circle, computed at render time from viewBox
  angle: (i / SEEDED_LOGINS.length) * Math.PI * 2 - Math.PI / 2,
}));

const SIZE = 320;
const CENTER = SIZE / 2;
const RADIUS = 118;

function pos(angle: number) {
  return { x: CENTER + RADIUS * Math.cos(angle), y: CENTER + RADIUS * Math.sin(angle) };
}

interface Pulse {
  key: string;
  from: { x: number; y: number };
  to: { x: number; y: number };
  width: number;
  agent: boolean;
}

export function TradeNetworkMap() {
  const trades = useMarketStore((s) => s.trades);
  const [pulses, setPulses] = useState<Pulse[]>([]);
  const lastSeen = useRef<number | null>(null);

  useEffect(() => {
    // Subscribed directly to the store (rather than reacting to the `trades`
    // prop in the effect body) so every setState here runs inside a
    // subscription callback responding to an external feed — not as a
    // synchronous side effect of render.
    const unsubscribe = useMarketStore.subscribe((state) => {
      const latest = state.trades[0];
      if (!latest || lastSeen.current === latest.id) return;
      lastSeen.current = latest.id;

      const fromNode = NODES.find((n) => n.id === latest.sellerTenantId);
      const toNode = NODES.find((n) => n.id === latest.buyerTenantId);
      if (!fromNode || !toNode) return;

      const pulse: Pulse = {
        key: `${latest.id}-${Date.now()}`,
        from: pos(fromNode.angle),
        to: pos(toNode.angle),
        width: Math.min(10, Math.max(1.5, latest.quantityMbps / 40)),
        agent: !!latest.isAgentTrade,
      };
      setPulses((p) => [...p, pulse]);
      setTimeout(() => setPulses((p) => p.filter((x) => x.key !== pulse.key)), 3200);
    });
    return unsubscribe;
  }, []);

  return (
    <Card>
      <CardHeader title="Live trade network" subtitle="Every fill draws a line between the two companies — unprompted" />
      <div className="flex justify-center p-4">
        <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="h-[280px] w-[280px] sm:h-[320px] sm:w-[320px]">
          {/* faint connective lattice */}
          {NODES.map((a) =>
            NODES.filter((b) => b.id !== a.id).map((b) => {
              const p1 = pos(a.angle);
              const p2 = pos(b.angle);
              return (
                <line
                  key={`${a.id}-${b.id}`}
                  x1={p1.x}
                  y1={p1.y}
                  x2={p2.x}
                  y2={p2.y}
                  stroke="var(--border)"
                  strokeWidth={1}
                  opacity={0.4}
                />
              );
            })
          )}

          <AnimatePresence>
            {pulses.map((p) => (
              <motion.line
                key={p.key}
                x1={p.from.x}
                y1={p.from.y}
                x2={p.to.x}
                y2={p.to.y}
                stroke={p.agent ? "var(--accent-2)" : "var(--accent)"}
                strokeWidth={p.width}
                strokeLinecap="round"
                initial={{ pathLength: 0, opacity: 0.9 }}
                animate={{ pathLength: 1, opacity: [0.9, 0.9, 0] }}
                exit={{ opacity: 0 }}
                transition={{ pathLength: { duration: 0.5, ease: "easeOut" }, opacity: { duration: 3, times: [0, 0.6, 1] } }}
                style={{ filter: `drop-shadow(0 0 6px ${p.agent ? "var(--accent-2)" : "var(--accent)"})` }}
              />
            ))}
          </AnimatePresence>

          {NODES.map((n) => {
            const p = pos(n.angle);
            return (
              <g key={n.id}>
                <circle cx={p.x} cy={p.y} r={26} fill="var(--surface-2)" stroke="var(--border)" strokeWidth={1.5} />
                <circle cx={p.x} cy={p.y} r={4} fill="var(--accent)" className="pulse-dot" style={{ transformOrigin: `${p.x}px ${p.y}px` }} />
                <text x={p.x} y={p.y + 40} textAnchor="middle" fontSize="10" fill="var(--muted)" fontFamily="var(--font-mono)">
                  {n.label.split(" ")[0]}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      {pulses.length > 0 && (
        <p className="border-t border-border px-4 py-2 text-center text-[11px] text-muted font-mono">
          latest: {fmtMbps(trades[0]?.quantityMbps ?? 0, 0)} clearing right now
        </p>
      )}
    </Card>
  );
}
