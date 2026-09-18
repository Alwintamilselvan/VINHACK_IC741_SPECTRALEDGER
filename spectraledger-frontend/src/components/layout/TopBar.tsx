"use client";

import { LogOut, Menu } from "lucide-react";
import { ConnectionDot } from "./ConnectionDot";
import { useConnStore } from "@/store/useConnStore";
import { useAuthStore } from "@/store/useAuthStore";
import { fmtUsd } from "@/lib/format";
import { useAccountStore } from "@/store/useAccountStore";

export function TopBar() {
  const java = useConnStore((s) => s.java);
  const ai = useConnStore((s) => s.ai);
  const { name, tenantId, logout } = useAuthStore();
  const account = useAccountStore((s) => s.account);

  return (
    <header className="flex items-center justify-between gap-4 border-b border-border bg-surface/60 backdrop-blur-sm px-5 py-3">
      <div className="flex items-center gap-3 lg:hidden">
        <Menu size={18} />
        <span className="font-display text-sm font-semibold">SpectraLedger</span>
      </div>

      <div className="hidden lg:flex items-center gap-5">
        <ConnectionDot label="Ledger API" state={java} />
        <ConnectionDot label="AI Engine" state={ai} />
      </div>

      <div className="flex items-center gap-4">
        {account && (
          <div className="hidden sm:block text-right">
            <p className="font-mono text-sm font-semibold leading-none">{fmtUsd(account.totalEquity)}</p>
            <p className="text-[10px] uppercase tracking-wide text-muted mt-1">Total equity</p>
          </div>
        )}
        {tenantId ? (
          <div className="flex items-center gap-2">
            <div className="text-right">
              <p className="text-sm font-medium leading-none">{name}</p>
              <p className="text-[10px] text-muted mt-1">Tenant</p>
            </div>
            <button
              onClick={logout}
              className="rounded-lg border border-border p-2 text-muted hover:text-danger hover:border-danger/40 transition-colors"
              aria-label="Log out"
            >
              <LogOut size={15} />
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}
