"use client";

import { motion } from "framer-motion";
import { Activity, Bot, Gauge, Network, ShieldCheck } from "lucide-react";

const FEATURES = [
  {
    icon: Activity,
    title: "Real-time waste prediction",
    body: "A live telemetry feed and a LightGBM forecast with a prediction interval continuously compute the gap between capacity and demand.",
  },
  {
    icon: Gauge,
    title: "Dynamic spot-pricing",
    body: "price = base_rate × congestion × QoS weight × urgency — fully explainable, every response includes the plain-English derivation.",
  },
  {
    icon: Bot,
    title: "Autonomous matching",
    body: "Seller and buyer agents re-evaluate every slice on their own schedule. Trades clear the instant a bid crosses an ask — no clicks required.",
  },
  {
    icon: Network,
    title: "Real order orchestration",
    body: "Cleared trades post as real orders to the settlement ledger, trigger a simulated NSSF slice reassignment, and settle buyer-to-seller in full.",
  },
  {
    icon: ShieldCheck,
    title: "Tamper-evident settlement",
    body: "ACID double-entry ledger with pessimistic row locking and a SHA-256 hash-chained audit trail — verifiable from genesis to tip, on demand.",
  },
];

export function FeatureGrid() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20">
      <motion.h2
        initial={{ opacity: 0, y: 14 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        className="mb-10 text-center font-display text-2xl font-semibold sm:text-3xl"
      >
        Everything a real exchange needs
      </motion.h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, delay: i * 0.06 }}
            className="rounded-2xl border border-border bg-surface/60 p-5 transition-colors hover:border-accent/30"
          >
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10 text-accent">
              <f.icon size={18} />
            </div>
            <h3 className="mb-1.5 font-display text-sm font-semibold">{f.title}</h3>
            <p className="text-xs leading-relaxed text-muted">{f.body}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
