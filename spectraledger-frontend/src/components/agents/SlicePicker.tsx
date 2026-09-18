"use client";

import { cn } from "@/lib/cn";
import type { DemoSlice } from "@/lib/types";

export function SlicePicker({
  fleet,
  selected,
  onSelect,
}: {
  fleet: DemoSlice[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {fleet.map((s) => (
        <button
          key={s.slice_id}
          onClick={() => onSelect(s.slice_id)}
          className={cn(
            "rounded-lg border px-3 py-2 text-left transition-colors",
            selected === s.slice_id ? "border-accent/50 bg-accent/10" : "border-border bg-surface-2 hover:border-accent/30"
          )}
        >
          <p className="font-mono text-xs font-semibold">{s.slice_id}</p>
          <p className="text-[10px] text-muted">{s.slice_type} · {s.capacity_mbps} Mbps</p>
        </button>
      ))}
    </div>
  );
}
