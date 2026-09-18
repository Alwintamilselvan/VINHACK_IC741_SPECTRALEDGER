// Formatting helpers. Every number on a trading-floor UI should render with
// tabular figures so columns never jitter as values stream in — enforced via
// the `font-mono tabular-nums` classes applied wherever these are used, plus
// fixed decimal counts here so string *lengths* stay stable too.

export function fmtUsd(value: number, decimals = 2): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function fmtUsdMicro(value: number): string {
  // for per-Mbps-minute prices, which are tiny (~0.0005-0.09)
  return `$${value.toFixed(6)}`;
}

export function fmtMbps(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)} Mbps`;
}

export function fmtPct(value: number, decimals = 0): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function fmtCompact(value: number): string {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(
    value
  );
}

export function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-US", { hour12: false });
  } catch {
    return "--:--:--";
  }
}

export function fmtRelative(iso: string): string {
  try {
    const ms = Date.now() - new Date(iso).getTime();
    if (ms < 1000) return "just now";
    if (ms < 60_000) return `${Math.floor(ms / 1000)}s ago`;
    if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
    return `${Math.floor(ms / 3_600_000)}h ago`;
  } catch {
    return "";
  }
}

export function shortHash(hash: string, len = 6): string {
  if (!hash) return "genesis";
  return `${hash.slice(0, len)}…${hash.slice(-len)}`;
}

export function shortId(id: string, len = 4): string {
  if (!id) return "";
  return id.length > len * 2 ? `${id.slice(0, len)}…${id.slice(-len)}` : id;
}

/** USD/Mbps-hour (AI engine unit) -> USD/Mbps-minute (Java backend unit). */
export function hourToMinuteRate(usdPerMbpsHour: number): number {
  return usdPerMbpsHour / 60;
}

export function minuteToHourRate(usdPerMbpsMin: number): number {
  return usdPerMbpsMin * 60;
}

export function clamp(v: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, v));
}
