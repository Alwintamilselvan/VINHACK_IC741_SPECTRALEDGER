"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Save, ShieldAlert } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { javaApi } from "@/lib/api/javaClient";
import { demoEngine } from "@/lib/demo/engine";
import { useAuthStore } from "@/store/useAuthStore";
import { useConnStore } from "@/store/useConnStore";
import { useAccountStore } from "@/store/useAccountStore";
import { fmtPct, fmtUsdMicro } from "@/lib/format";
import type { AdminSettings } from "@/lib/types";

const TIERS = [
  { key: "priceFloorBronze", label: "Bronze" },
  { key: "priceFloorSilver", label: "Silver" },
  { key: "priceFloorGold", label: "Gold" },
  { key: "priceFloorPlatinum", label: "Platinum" },
] as const;

export function RiskControls() {
  const settings = useAccountStore((s) => s.adminSettings);

  return (
    <Card>
      <CardHeader
        title="Risk controls"
        subtitle="Effective on the very next order submitted, enforced server-side"
        right={<ShieldAlert size={16} className="text-warning" />}
      />
      {!settings ? (
        <div className="space-y-4 p-5">
          <div className="h-4 w-1/3 rounded skeleton" />
          <div className="h-2 w-full rounded skeleton" />
          <div className="grid grid-cols-2 gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-14 rounded skeleton" />
            ))}
          </div>
        </div>
      ) : (
        // Keyed by updatedAt: a fresh settings snapshot from the server mounts
        // a fresh form with that snapshot as its starting point, so local
        // edits never fight an external sync effect.
        <RiskControlsForm key={settings.updatedAt} initial={settings} />
      )}
    </Card>
  );
}

function RiskControlsForm({ initial }: { initial: AdminSettings }) {
  const setAdminSettings = useAccountStore((s) => s.setAdminSettings);
  const { token, tenantId } = useAuthStore();
  const java = useConnStore((s) => s.java);

  const [buffer, setBuffer] = useState(initial.safetyBufferPercent);
  const [floors, setFloors] = useState({
    priceFloorBronze: initial.priceFloorBronze,
    priceFloorSilver: initial.priceFloorSilver,
    priceFloorGold: initial.priceFloorGold,
    priceFloorPlatinum: initial.priceFloorPlatinum,
  });
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  async function save() {
    setSaving(true);
    const patch = { safetyBufferPercent: buffer, ...floors };
    try {
      if (token && java === "live") {
        const res = await javaApi.updateAdminSettings(token, patch);
        setAdminSettings(res);
      } else if (tenantId) {
        setAdminSettings(demoEngine.updateAdmin(patch));
      }
      setSavedAt(Date.now());
    } finally {
      setSaving(false);
    }
  }

  const sellableExample = Math.round(300 * buffer);

  return (
    <div className="space-y-6 p-5">
      <div>
        <div className="mb-1 flex items-center justify-between text-xs">
          <label className="uppercase tracking-wide text-muted">Safety buffer</label>
          <span className="font-mono text-accent">{fmtPct(buffer)}</span>
        </div>
        <input
          type="range"
          min={0}
          max={0.4}
          step={0.01}
          value={buffer}
          onChange={(e) => setBuffer(Number(e.target.value))}
          className="w-full accent-[var(--accent)]"
        />
        <motion.p key={sellableExample} initial={{ opacity: 0.4 }} animate={{ opacity: 1 }} className="mt-2 text-[11px] text-muted">
          &ldquo;Never lease below {fmtPct(buffer)} internal reserve&rdquo; &rarr; on a 300 Mbps slice that reserves{" "}
          <span className="font-mono text-accent">{sellableExample} Mbps</span> before anything is ever listed.
        </motion.p>
      </div>

      <div>
        <p className="mb-2 text-xs uppercase tracking-wide text-muted">Price floors (USD / Mbps-min)</p>
        <div className="grid grid-cols-2 gap-3">
          {TIERS.map((t) => (
            <div key={t.key}>
              <label className="mb-1 block text-[10px] text-muted">{t.label}</label>
              <input
                type="number"
                step="0.01"
                value={floors[t.key]}
                onChange={(e) => setFloors((f) => ({ ...f, [t.key]: Number(e.target.value) }))}
                className="w-full rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 font-mono text-sm outline-none focus:border-accent/50"
              />
              <p className="mt-0.5 font-mono text-[10px] text-muted">{fmtUsdMicro(floors[t.key])}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Button onClick={save} disabled={saving}>
          <Save size={14} /> {saving ? "Saving…" : "Save settings"}
        </Button>
        {savedAt && <span className="text-[11px] text-success">Applied to the next order.</span>}
      </div>
    </div>
  );
}
