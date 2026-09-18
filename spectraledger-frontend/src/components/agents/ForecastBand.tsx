"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { Trend } from "@/lib/types";
import { fmtMbps } from "@/lib/format";

export interface ForecastPoint {
  t: number;
  predicted: number;
  lower: number;
  upper: number;
}

const W = 560;
const H = 180;
const PAD = 24;

export function ForecastBand({
  points,
  capacityMbps,
  trend,
  confidence,
}: {
  points: ForecastPoint[];
  capacityMbps: number;
  trend: Trend;
  confidence: number;
}) {
  const { linePath, bandPath, capY } = useMemo(() => {
    if (points.length < 2) return { linePath: "", bandPath: "", capY: 0 };
    const maxVal = Math.max(capacityMbps, ...points.map((p) => p.upper)) * 1.05;
    const minVal = Math.min(...points.map((p) => p.lower)) * 0.9;
    const xAt = (i: number) => PAD + (i / (points.length - 1)) * (W - PAD * 2);
    const yAt = (v: number) => H - PAD - ((v - minVal) / (maxVal - minVal || 1)) * (H - PAD * 2);

    const line = points.map((p, i) => `${i === 0 ? "M" : "L"} ${xAt(i)} ${yAt(p.predicted)}`).join(" ");
    const upperPath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${xAt(i)} ${yAt(p.upper)}`).join(" ");
    const lowerPath = [...points]
      .reverse()
      .map((p, i) => `L ${xAt(points.length - 1 - i)} ${yAt(p.lower)}`)
      .join(" ");
    return { linePath: line, bandPath: `${upperPath} ${lowerPath} Z`, capY: yAt(capacityMbps) };
  }, [points, capacityMbps]);

  const latest = points[points.length - 1];

  return (
    <Card>
      <CardHeader
        title="Demand forecast"
        subtitle="15–60 min ahead, with prediction interval"
        right={
          latest && (
            <Badge tone={trend === "rising" ? "danger" : trend === "falling" ? "accent" : "neutral"}>{trend}</Badge>
          )
        }
      />
      <div className="p-4">
        {points.length < 2 ? (
          <div className="h-[180px] w-full rounded-xl skeleton" />
        ) : (
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
            <line x1={PAD} y1={capY} x2={W - PAD} y2={capY} stroke="var(--warning)" strokeDasharray="4 4" strokeWidth={1} />
            <text x={W - PAD} y={capY - 6} textAnchor="end" fontSize="9" fill="var(--warning)" fontFamily="var(--font-mono)">
              capacity {fmtMbps(capacityMbps, 0)}
            </text>
            <motion.path d={bandPath} fill="var(--accent)" opacity={0.12} initial={false} animate={{ d: bandPath }} transition={{ duration: 0.4 }} />
            <motion.path
              d={linePath}
              fill="none"
              stroke="var(--accent)"
              strokeWidth={2}
              initial={false}
              animate={{ d: linePath }}
              transition={{ duration: 0.4 }}
              style={{ filter: "drop-shadow(0 0 4px var(--accent))" }}
            />
          </svg>
        )}
        <div className="mt-2 flex items-center justify-between text-xs">
          <span className="font-mono text-muted">
            {latest ? `${fmtMbps(latest.lower, 0)} – ${fmtMbps(latest.upper, 0)}` : "—"}
          </span>
          <span className="font-mono text-accent">confidence {Math.round(confidence * 100)}%</span>
        </div>
      </div>
    </Card>
  );
}
