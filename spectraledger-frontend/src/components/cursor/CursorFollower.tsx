"use client";

import { useEffect, useState } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";

/**
 * A soft glow-ring cursor follower for the marketing/landing page only.
 *
 * Deliberately NOT used inside the trading terminal: once the app becomes a
 * dense grid of order-book rows, ledger tables and small click targets, a
 * custom cursor competes with the native pointer exactly where precision
 * matters most — that's a real usability cost on a page whose whole premise
 * is "read fast, click fast." On a hero/landing page there's no such cost,
 * and the motion sells the "alive, premium" feeling the pitch is going for.
 * See README "Design decisions" for the full reasoning.
 */
export default function CursorFollower() {
  const [visible, setVisible] = useState(false);
  const [hovering, setHovering] = useState(false);
  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const springX = useSpring(x, { damping: 28, stiffness: 320, mass: 0.4 });
  const springY = useSpring(y, { damping: 28, stiffness: 320, mass: 0.4 });

  useEffect(() => {
    const coarse = window.matchMedia?.("(pointer: coarse)").matches;
    if (coarse) return; // skip entirely on touch devices

    const move = (e: MouseEvent) => {
      x.set(e.clientX);
      y.set(e.clientY);
      if (!visible) setVisible(true);
      const target = e.target as HTMLElement;
      setHovering(!!target.closest("a,button,[data-cursor-hover]"));
    };
    const leave = () => setVisible(false);
    window.addEventListener("mousemove", move);
    document.documentElement.addEventListener("mouseleave", leave);
    return () => {
      window.removeEventListener("mousemove", move);
      document.documentElement.removeEventListener("mouseleave", leave);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible]);

  return (
    <motion.div
      aria-hidden
      className="pointer-events-none fixed left-0 top-0 z-[60] mix-blend-difference hidden md:block"
      style={{ x: springX, y: springY, translateX: "-50%", translateY: "-50%" }}
      animate={{ opacity: visible ? 1 : 0, scale: hovering ? 2.2 : 1 }}
      transition={{ opacity: { duration: 0.2 }, scale: { type: "spring", damping: 20, stiffness: 260 } }}
    >
      <div className="h-6 w-6 rounded-full border border-white" />
    </motion.div>
  );
}
