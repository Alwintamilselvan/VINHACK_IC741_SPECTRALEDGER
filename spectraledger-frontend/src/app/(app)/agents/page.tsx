"use client";

import { useEffect, useState } from "react";
import { aiApi } from "@/lib/api/aiClient";
import { demoEngine } from "@/lib/demo/engine";
import { useConnStore } from "@/store/useConnStore";
import { useMarketStore } from "@/store/useMarketStore";
import { SlicePicker } from "@/components/agents/SlicePicker";
import { ForecastBand, type ForecastPoint } from "@/components/agents/ForecastBand";
import { PriceFormula } from "@/components/agents/PriceFormula";
import { SLAGauge } from "@/components/agents/SLAGauge";
import { ReasoningFeed } from "@/components/agents/ReasoningFeed";
import { Card, CardHeader } from "@/components/ui/Card";
import type { PriceComponents, Trend } from "@/lib/types";

export default function AgentsPage() {
  const fleet = useMarketStore((s) => s.fleet);
  const [manualSliceId, setManualSliceId] = useState<string | null>(null);
  const activeSliceId = manualSliceId ?? fleet[0]?.slice_id ?? "";
  const activeFleetSlice = fleet.find((f) => f.slice_id === activeSliceId);

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <div>
        <h1 className="font-display text-2xl font-semibold">Agents &amp; AI</h1>
        <p className="text-sm text-muted">Forecasting, transparent pricing, and the autonomous buyer/seller loop.</p>
      </div>

      <Card>
        <CardHeader title="Select a slice" subtitle="Seven simulated companies, each its own private 5G slice" />
        <div className="p-4">
          <SlicePicker fleet={fleet} selected={activeSliceId} onSelect={setManualSliceId} />
        </div>
      </Card>

      {activeSliceId && (
        <SliceIntelPanel key={activeSliceId} sliceId={activeSliceId} capacityMbps={activeFleetSlice?.capacity_mbps ?? 1000} />
      )}
    </div>
  );
}

/**
 * Remounted (via `key={sliceId}` on the parent) whenever the selected slice
 * changes, so its local state starts fresh naturally instead of needing an
 * effect to reset it — that keeps every remaining effect a pure "subscribe
 * to an external feed, apply what comes back" effect.
 */
function SliceIntelPanel({ sliceId, capacityMbps }: { sliceId: string; capacityMbps: number }) {
  const ai = useConnStore((s) => s.ai);
  const [points, setPoints] = useState<ForecastPoint[]>([]);
  const [trend, setTrend] = useState<Trend>("stable");
  const [confidence, setConfidence] = useState(0);
  const [gatePassed, setGatePassed] = useState(true);
  const [priceComponents, setPriceComponents] = useState<PriceComponents | null>(null);
  const [midPrice, setMidPrice] = useState(0);
  const [explanation, setExplanation] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        if (ai === "live") {
          const [f, p] = await Promise.all([aiApi.forecast({ slice_id: sliceId }), aiApi.price({ slice_id: sliceId })]);
          if (cancelled) return;
          setTrend(f.trend);
          setConfidence(f.confidence_score);
          setPriceComponents(p.components);
          setMidPrice(p.mid_price);
          setExplanation(p.explanation);
          setPoints((prev) => [...prev, { t: Date.now(), predicted: f.predicted_demand_mbps, lower: f.confidence_interval.lower, upper: f.confidence_interval.upper }].slice(-20));
          setGatePassed(f.confidence_score >= 0.5);
        } else {
          const fc = demoEngine.getForecast(sliceId);
          const pr = demoEngine.getPrice(sliceId);
          if (!fc || !pr || cancelled) return;
          setTrend(fc.forecast.trend);
          setConfidence(fc.forecast.confidence);
          setPriceComponents(pr.price.components);
          setMidPrice(pr.price.mid);
          setExplanation(pr.price.explanation);
          setPoints((prev) => [...prev, { t: Date.now(), predicted: fc.forecast.predicted, lower: fc.forecast.lower, upper: fc.forecast.upper }].slice(-20));
          setGatePassed(fc.forecast.confidence >= 0.5);
        }
      } catch {
        /* keep last good frame on a transient failure */
      }
    }
    poll();
    const t = setInterval(poll, 3000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [sliceId, ai]);

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
      <div className="lg:col-span-2 space-y-5">
        <ForecastBand points={points} capacityMbps={capacityMbps} trend={trend} confidence={confidence} />
        {priceComponents && <PriceFormula components={priceComponents} midPrice={midPrice} explanation={explanation} />}
      </div>
      <div className="space-y-5">
        <Card className="flex flex-col items-center justify-center p-6">
          <p className="mb-3 text-xs uppercase tracking-wide text-muted">SLA risk gate</p>
          <SLAGauge confidence={confidence} slaGatePassed={gatePassed} />
        </Card>
        <div className="h-[420px]">
          <ReasoningFeed />
        </div>
      </div>
    </div>
  );
}
