"use client";

import { motion } from "framer-motion";
import { Radio } from "lucide-react";

const BARS = [0.4, 0.75, 1, 0.6, 0.85, 0.5, 0.9];

/**
 * Replaces every blank loading state in the app. Themed as a signal
 * acquisition sweep — on-brand for a spectrum/bandwidth product — rather
 * than a generic spinner, so even the "nothing to show yet" moment reads
 * as part of the product instead of a stall.
 */
export function LoadingScene({ label = "Acquiring signal…" }: { label?: string }) {
  return (
    <div className="flex min-h-[50vh] w-full flex-col items-center justify-center gap-6 py-16">
      <div className="relative flex h-16 w-16 items-center justify-center">
        <motion.span
          className="absolute inset-0 rounded-full border border-accent/40"
          animate={{ scale: [1, 1.8, 1.8], opacity: [0.6, 0, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
        />
        <motion.span
          className="absolute inset-0 rounded-full border border-accent/40"
          animate={{ scale: [1, 1.8, 1.8], opacity: [0.6, 0, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut", delay: 0.6 }}
        />
        <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-accent/10 text-accent">
          <Radio size={20} />
        </div>
      </div>

      <div className="flex items-end gap-1 h-8">
        {BARS.map((h, i) => (
          <motion.span
            key={i}
            className="w-1.5 rounded-full bg-accent/70"
            animate={{ scaleY: [0.3, h, 0.3] }}
            transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.09, ease: "easeInOut" }}
            style={{ height: 32, transformOrigin: "bottom" }}
          />
        ))}
      </div>

      <p className="font-mono text-xs uppercase tracking-widest text-muted">{label}</p>
    </div>
  );
}
