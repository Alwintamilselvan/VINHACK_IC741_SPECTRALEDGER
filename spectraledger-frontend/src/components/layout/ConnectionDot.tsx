import { cn } from "@/lib/cn";
import type { ConnState } from "@/lib/types";

const styles: Record<ConnState, { dot: string; label: string }> = {
  live: { dot: "bg-success", label: "LIVE" },
  connecting: { dot: "bg-warning", label: "CONNECTING" },
  demo: { dot: "bg-accent-2", label: "DEMO" },
  offline: { dot: "bg-danger", label: "OFFLINE" },
};

export function ConnectionDot({ label, state }: { label: string; state: ConnState }) {
  const s = styles[state];
  return (
    <div className="flex items-center gap-1.5 font-mono text-[11px] text-muted">
      <span className="relative flex h-2 w-2">
        <span className={cn("absolute inline-flex h-full w-full rounded-full opacity-75", s.dot, state !== "demo" && "pulse-dot")} />
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", s.dot)} />
      </span>
      <span className="uppercase tracking-wide">{label}</span>
      <span className={cn("uppercase tracking-wide font-semibold", state === "live" ? "text-success" : state === "demo" ? "text-accent-2" : state === "connecting" ? "text-warning" : "text-danger")}>
        {s.label}
      </span>
    </div>
  );
}
