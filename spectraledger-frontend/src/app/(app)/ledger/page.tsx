"use client";

import { AccountBreakdown } from "@/components/ledger/AccountBreakdown";
import { LedgerChain } from "@/components/ledger/LedgerChain";
import { VerifyChainButton } from "@/components/ledger/VerifyChainButton";
import { useAccountStore } from "@/store/useAccountStore";

export default function LedgerPage() {
  const account = useAccountStore((s) => s.account);
  const ledger = useAccountStore((s) => s.ledger);
  const slices = useAccountStore((s) => s.slices);

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <div>
        <h1 className="font-display text-2xl font-semibold">Ledger &amp; account</h1>
        <p className="text-sm text-muted">ACID-guaranteed double-entry settlement, with a tamper-evident audit trail.</p>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-5">
          <AccountBreakdown account={account} />
          <LedgerChain entries={ledger} />
        </div>
        <div className="space-y-5">
          <VerifyChainButton />
          <div className="rounded-2xl border border-border bg-surface/70 p-5">
            <p className="mb-3 font-display text-sm font-semibold uppercase tracking-wide">My slices</p>
            <div className="space-y-2">
              {slices.length === 0 ? (
                <p className="text-xs text-muted">No slices yet.</p>
              ) : (
                slices.map((s) => (
                  <div key={s.id} className="rounded-lg border border-border bg-surface-2/60 p-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-semibold">{s.qosTier}</span>
                      <span className="font-mono text-muted">{s.totalCapacityMbps} Mbps</span>
                    </div>
                    <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/5">
                      <div
                        className="h-full rounded-full bg-accent"
                        style={{ width: `${(s.allocatedMbps / s.totalCapacityMbps) * 100}%` }}
                      />
                    </div>
                    <div className="mt-1 flex justify-between text-[10px] text-muted">
                      <span>{s.allocatedMbps} allocated</span>
                      <span>{s.availableMbps} available</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
