"use client";

import Link from "next/link";
import { useRef } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";
import { ArrowRight, Radio } from "lucide-react";
import { useMarketStore } from "@/store/useMarketStore";
import { useCountUp } from "@/hooks/useCountUp";

function MagneticLink({ href, children, primary }: { href: string; children: React.ReactNode; primary?: boolean }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 200, damping: 15, mass: 0.4 });
  const springY = useSpring(y, { stiffness: 200, damping: 15, mass: 0.4 });

  function onMouseMove(e: React.MouseEvent) {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    x.set((e.clientX - (rect.left + rect.width / 2)) * 0.25);
    y.set((e.clientY - (rect.top + rect.height / 2)) * 0.25);
  }
  function onMouseLeave() {
    x.set(0);
    y.set(0);
  }

  return (
    <motion.div ref={ref} style={{ x: springX, y: springY }} onMouseMove={onMouseMove} onMouseLeave={onMouseLeave}>
      <Link
        href={href}
        data-cursor-hover
        className={
          primary
            ? "inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-background shadow-[0_0_32px_-6px_var(--accent)] transition-transform hover:scale-[1.03]"
            : "inline-flex items-center gap-2 rounded-full border border-border px-6 py-3 text-sm font-medium text-foreground/80 transition-colors hover:border-accent/40 hover:text-foreground"
        }
      >
        {children}
      </Link>
    </motion.div>
  );
}

export function Hero() {
  const trades = useMarketStore((s) => s.trades);
  const fleet = useMarketStore((s) => s.fleet);
  const tradeCount = useCountUp(trades.length);

  return (
    <section className="relative flex min-h-[92vh] flex-col items-center justify-center overflow-hidden px-4 text-center">
      <div className="pointer-events-none absolute inset-0 -z-10 [background:radial-gradient(circle_at_50%_18%,color-mix(in_srgb,var(--accent)_14%,transparent),transparent_55%)]" />
      <div
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.07]"
        style={{
          backgroundImage: "linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)",
          backgroundSize: "42px 42px",
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-6 flex items-center gap-2 rounded-full border border-accent/25 bg-accent/5 px-4 py-1.5 font-mono text-[11px] uppercase tracking-widest text-accent"
      >
        <Radio size={12} className="pulse-dot" /> Live now · {fleet.length || 7} companies · {tradeCount.toFixed(0)} trades cleared this session
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.05 }}
        className="max-w-4xl font-display text-4xl font-bold leading-[1.05] sm:text-6xl"
      >
        Idle 5G bandwidth,
        <br />
        <span className="bg-gradient-to-r from-accent via-accent to-accent-2 bg-clip-text text-transparent">
          traded like an asset.
        </span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.15 }}
        className="mt-5 max-w-xl text-balance text-base text-muted sm:text-lg"
      >
        SpectraLedger forecasts surplus network slices, prices them with a transparent formula, and lets autonomous
        agents clear trades between enterprises — seconds after a shortfall appears, zero human input required.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.25 }}
        className="mt-8 flex flex-wrap items-center justify-center gap-3"
      >
        <MagneticLink href="/login" primary>
          Enter the trading floor <ArrowRight size={15} />
        </MagneticLink>
        <MagneticLink href="#how-it-works">See how it works</MagneticLink>
      </motion.div>
    </section>
  );
}
