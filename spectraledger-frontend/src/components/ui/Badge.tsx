import { cn } from "@/lib/cn";

type Tone = "neutral" | "accent" | "accent2" | "success" | "warning" | "danger";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-white/5 text-foreground/80 border-border",
  accent: "bg-accent/10 text-accent border-accent/30",
  accent2: "bg-accent-2/10 text-accent-2 border-accent-2/30",
  success: "bg-success/10 text-success border-success/30",
  warning: "bg-warning/10 text-warning border-warning/30",
  danger: "bg-danger/10 text-danger border-danger/30",
};

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-mono font-medium uppercase tracking-wide",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
