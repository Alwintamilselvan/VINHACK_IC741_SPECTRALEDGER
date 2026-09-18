"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BrainCircuit, LayoutGrid, ScrollText, Settings, Radio } from "lucide-react";
import { cn } from "@/lib/cn";
import { useAuthStore } from "@/store/useAuthStore";

const NAV = [
  { href: "/dashboard", label: "Trading Floor", icon: LayoutGrid },
  { href: "/agents", label: "Agents & AI", icon: BrainCircuit },
  { href: "/ledger", label: "Ledger & Account", icon: ScrollText },
  { href: "/admin", label: "Risk Admin", icon: Settings, adminOnly: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const role = useAuthStore((s) => s.role);

  return (
    <aside className="hidden lg:flex w-60 shrink-0 flex-col border-r border-border bg-surface/60 backdrop-blur-sm">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/10 text-accent">
          <Radio size={16} />
        </div>
        <div>
          <p className="font-display text-sm font-semibold leading-none">SpectraLedger</p>
          <p className="text-[10px] uppercase tracking-widest text-muted mt-1">Spectrum Clearinghouse</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-2">
        {NAV.filter((item) => !item.adminOnly || role === "ADMIN").map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                active
                  ? "bg-accent/10 text-accent border border-accent/20"
                  : "text-foreground/70 hover:text-foreground hover:bg-white/5 border border-transparent"
              )}
            >
              <Icon size={16} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-4 border-t border-border">
        <div className="flex items-center gap-2 text-[11px] text-muted">
          <Activity size={13} className="text-accent" />
          Autonomous agents run with zero manual input.
        </div>
      </div>
    </aside>
  );
}
