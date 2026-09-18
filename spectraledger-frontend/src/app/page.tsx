import CursorFollower from "@/components/cursor/CursorFollower";
import { Hero } from "@/components/landing/Hero";
import { LiveTicker } from "@/components/landing/LiveTicker";
import { FeatureGrid } from "@/components/landing/FeatureGrid";
import { HowItWorks } from "@/components/landing/HowItWorks";

export default function LandingPage() {
  return (
    <div className="relative">
      {/* Cursor follower is intentionally scoped to this marketing page only —
          see CursorFollower.tsx for why it stays off the trading terminal. */}
      <CursorFollower />
      <Hero />
      <LiveTicker />
      <FeatureGrid />
      <HowItWorks />
      <footer className="border-t border-border px-4 py-8 text-center text-xs text-muted">
        SpectraLedger — autonomous 5G spectrum arbitrage &amp; enterprise bandwidth clearinghouse.
      </footer>
    </div>
  );
}
