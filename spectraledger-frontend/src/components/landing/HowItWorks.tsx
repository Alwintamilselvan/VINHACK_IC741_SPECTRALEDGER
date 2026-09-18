"use client";

import { motion } from "framer-motion";

const STEPS = [
  {
    n: "01",
    title: "Forecast the surplus",
    body: "Every slice's telemetry streams in continuously. A demand model predicts utilization 15–60 minutes out, with a confidence score attached.",
  },
  {
    n: "02",
    title: "Price it transparently",
    body: "A four-factor formula converts congestion, QoS tier and urgency into a bid/ask spread — and explains itself in plain English every time.",
  },
  {
    n: "03",
    title: "Clear it autonomously",
    body: "Buyer and seller agents submit real orders on their own schedule. The moment a bid crosses an ask, the trade settles — like a real exchange.",
  },
  {
    n: "04",
    title: "Settle & reassign",
    body: "Double-entry ledger settlement fires instantly; a simulated 5G slice reassignment confirms moments later, visible live on the trade tape.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="mx-auto max-w-5xl px-4 py-20">
      <motion.h2
        initial={{ opacity: 0, y: 14 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        className="mb-12 text-center font-display text-2xl font-semibold sm:text-3xl"
      >
        How a trade happens, start to finish
      </motion.h2>
      <div className="relative space-y-8">
        <div className="absolute left-[19px] top-2 bottom-2 hidden w-px bg-border sm:block" />
        {STEPS.map((s, i) => (
          <motion.div
            key={s.n}
            initial={{ opacity: 0, x: -16 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, delay: i * 0.08 }}
            className="relative flex gap-5 sm:pl-0"
          >
            <div className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-accent/30 bg-surface font-mono text-xs text-accent">
              {s.n}
            </div>
            <div className="pt-1.5">
              <h3 className="font-display text-base font-semibold">{s.title}</h3>
              <p className="mt-1 max-w-xl text-sm text-muted">{s.body}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
