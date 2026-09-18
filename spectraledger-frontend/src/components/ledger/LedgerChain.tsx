"use client";

import { motion } from "framer-motion";
import { Link2 } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import type { LedgerEntry } from "@/lib/types";
import { fmtTime, fmtUsd, shortHash } from "@/lib/format";
import { cn } from "@/lib/cn";

export function LedgerChain({ entries }: { entries: LedgerEntry[] }) {
  const ordered = [...entries].sort((a, b) => a.id - b.id);

  return (
    <Card>
      <CardHeader title="Double-entry ledger" subtitle="Tamper-evident: each entry hashes in the previous one" />
      <div className="max-h-[420px] overflow-y-auto">
        {ordered.length === 0 ? (
          <div className="space-y-2 p-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-12 w-full rounded skeleton" />
            ))}
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface text-[10px] uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 text-left font-normal">Entry</th>
                <th className="px-2 py-2 text-left font-normal">Description</th>
                <th className="px-2 py-2 text-right font-normal">Amount</th>
                <th className="px-2 py-2 text-right font-normal">Balance after</th>
                <th className="px-4 py-2 text-right font-normal">Hash</th>
              </tr>
            </thead>
            <tbody>
              {ordered.map((e, i) => (
                <motion.tr
                  key={e.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: Math.min(i * 0.02, 0.3) }}
                  className="border-t border-border/60 hover:bg-white/[0.02]"
                >
                  <td className="whitespace-nowrap px-4 py-2 font-mono text-muted">
                    <span className="flex items-center gap-1.5">
                      {i > 0 && <Link2 size={10} className="text-accent/50" />}#{e.id}
                    </span>
                    <span className="block text-[10px]">{fmtTime(e.createdAt)}</span>
                  </td>
                  <td className="px-2 py-2 text-foreground/80">{e.description}</td>
                  <td className={cn("whitespace-nowrap px-2 py-2 text-right font-mono", e.entryType === "CREDIT" ? "text-success" : "text-danger")}>
                    {e.entryType === "CREDIT" ? "+" : "−"}
                    {fmtUsd(e.amount)}
                  </td>
                  <td className="whitespace-nowrap px-2 py-2 text-right font-mono">{fmtUsd(e.balanceAfter)}</td>
                  <td className="whitespace-nowrap px-4 py-2 text-right font-mono text-[10px] text-muted" title={e.entryHash}>
                    {shortHash(e.entryHash)}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Card>
  );
}
