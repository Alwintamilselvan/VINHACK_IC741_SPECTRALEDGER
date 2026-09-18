"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldCheck, ShieldAlert, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { javaApi } from "@/lib/api/javaClient";
import { demoEngine } from "@/lib/demo/engine";
import { useAuthStore } from "@/store/useAuthStore";
import { useConnStore } from "@/store/useConnStore";
import type { ChainVerification } from "@/lib/types";

export function VerifyChainButton() {
  const { token, tenantId, demoLoggedIn } = useAuthStore();
  const java = useConnStore((s) => s.java);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ChainVerification | null>(null);

  async function verify() {
    if (!tenantId) return;
    setLoading(true);
    setResult(null);
    const start = Date.now();
    try {
      const res =
        token && java === "live" ? await javaApi.verifyChain(token) : await demoEngine.verifyChain(tenantId);
      // keep the animation legible even when the check is instant
      const elapsed = Date.now() - start;
      if (elapsed < 700) await new Promise((r) => setTimeout(r, 700 - elapsed));
      setResult(res);
    } catch {
      setResult(await demoEngine.verifyChain(tenantId));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-accent/20 bg-gradient-to-b from-accent/5 to-transparent p-6 text-center">
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Loader2 className="animate-spin text-accent" size={40} />
          </motion.div>
        ) : result ? (
          <motion.div
            key="result"
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "spring", damping: 12, stiffness: 200 }}
          >
            {result.valid ? (
              <ShieldCheck size={44} className="text-success drop-shadow-[0_0_12px_var(--success)]" />
            ) : (
              <ShieldAlert size={44} className="text-danger drop-shadow-[0_0_12px_var(--danger)]" />
            )}
          </motion.div>
        ) : (
          <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <ShieldCheck size={44} className="text-muted" />
          </motion.div>
        )}
      </AnimatePresence>

      <div>
        <p className="font-display text-sm font-semibold">Verify ledger integrity</p>
        <p className="mt-1 max-w-xs text-xs text-muted">
          Recomputes the hash chain from genesis to tip — a broken link anywhere means a rejected write.
        </p>
      </div>

      {result && (
        <p className={result.valid ? "text-xs text-success" : "text-xs text-danger"}>{result.message}</p>
      )}

      <Button onClick={verify} disabled={loading} variant="secondary">
        {loading ? "Verifying…" : "Run verification"}
      </Button>
      {!demoLoggedIn && java !== "live" && (
        <p className="text-[10px] text-accent-2">Verifying against the simulated chain (ledger API offline).</p>
      )}
    </div>
  );
}
