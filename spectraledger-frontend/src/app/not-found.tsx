"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/Button";

function Waveform({ dead }: { dead: boolean }) {
  const [seed, setSeed] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSeed((s) => s + 1), 1400);
    return () => clearInterval(t);
  }, []);

  const points = Array.from({ length: 48 }, (_, i) => {
    if (dead) return 40;
    const spike = (i + seed) % 12 === 0 ? 26 : (i + seed) % 7 === 0 ? -22 : 0;
    return 40 + Math.sin(i * 0.7 + seed) * 6 + spike;
  });
  const path = points.map((y, i) => `${i === 0 ? "M" : "L"} ${i * 12} ${y}`).join(" ");

  return (
    <svg viewBox="0 0 576 80" className="w-full max-w-lg">
      <motion.path
        d={path}
        fill="none"
        stroke="var(--danger)"
        strokeWidth={2}
        animate={{ d: path }}
        transition={{ duration: 0.5 }}
        style={{ filter: "drop-shadow(0 0 6px var(--danger))" }}
      />
    </svg>
  );
}

export default function NotFound() {
  const [lost, setLost] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setLost(true), 1800);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background px-4 text-center">
      <div className="pointer-events-none absolute inset-0 [background:radial-gradient(circle_at_50%_30%,color-mix(in_srgb,var(--danger)_10%,transparent),transparent_55%)]" />

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="relative select-none"
      >
        <motion.h1
          className="font-display text-[6rem] font-bold leading-none sm:text-[9rem]"
          animate={{
            textShadow: [
              "2px 0 var(--accent-2), -2px 0 var(--danger)",
              "-2px 0 var(--accent-2), 2px 0 var(--danger)",
              "1px 0 var(--accent-2), -1px 0 var(--danger)",
              "0 0 transparent, 0 0 transparent",
            ],
            x: [0, -2, 2, 0],
          }}
          transition={{ duration: 2.4, repeat: Infinity, repeatDelay: 1.2 }}
        >
          404
        </motion.h1>
      </motion.div>

      <div className="my-4 flex items-center gap-2 text-danger">
        <WifiOff size={16} />
        <span className="font-mono text-xs uppercase tracking-widest">
          {lost ? "signal lost — 0 Mbps allocated to this route" : "checking slice allocation…"}
        </span>
      </div>

      <Waveform dead={lost} />

      <p className="mt-6 max-w-sm text-sm text-muted">
        This route was never provisioned a slice. No bandwidth, no page — but the rest of the exchange is still
        clearing trades without you.
      </p>

      <div className="mt-6 flex gap-3">
        <Link href="/dashboard">
          <Button>
            <ArrowLeft size={14} /> Back to the trading floor
          </Button>
        </Link>
        <Link href="/">
          <Button variant="secondary">Home</Button>
        </Link>
      </div>
    </div>
  );
}
