"use client";

import { Card, CardHeader } from "@/components/ui/Card";
import type { Account } from "@/lib/types";
import { fmtUsd } from "@/lib/format";
import { useCountUp } from "@/hooks/useCountUp";

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  const animated = useCountUp(value);
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-muted">{label}</p>
      <p className="font-mono text-xl font-semibold" style={{ color }}>
        {fmtUsd(animated)}
      </p>
    </div>
  );
}

export function AccountBreakdown({ account }: { account: Account | null }) {
  if (!account) {
    return (
      <Card>
        <CardHeader title="Account" subtitle="Balance · escrow · equity" />
        <div className="space-y-3 p-5">
          <div className="h-6 w-2/3 rounded skeleton" />
          <div className="h-3 w-full rounded skeleton" />
          <div className="h-6 w-1/2 rounded skeleton" />
        </div>
      </Card>
    );
  }

  const balancePct = account.totalEquity > 0 ? (account.balance / account.totalEquity) * 100 : 50;

  return (
    <Card>
      <CardHeader title={account.name} subtitle={`@${account.username} · ${account.role}`} />
      <div className="grid grid-cols-3 gap-4 p-5">
        <Stat label="Available balance" value={account.balance} color="var(--accent)" />
        <Stat label="In escrow" value={account.escrowBalance} color="var(--warning)" />
        <Stat label="Total equity" value={account.totalEquity} color="var(--foreground)" />
      </div>
      <div className="px-5 pb-5">
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-warning/20">
          <div
            className="h-full rounded-full bg-accent transition-all duration-700 ease-out"
            style={{ width: `${balancePct}%` }}
          />
        </div>
        <div className="mt-1.5 flex justify-between text-[10px] text-muted">
          <span>Liquid</span>
          <span>Locked in open bids</span>
        </div>
      </div>
    </Card>
  );
}
