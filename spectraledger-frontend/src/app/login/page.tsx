"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Radio, ArrowRight, ShieldCheck } from "lucide-react";
import { javaApi, JavaApiError } from "@/lib/api/javaClient";
import { useAuthStore } from "@/store/useAuthStore";
import { useConnStore } from "@/store/useConnStore";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ADMIN_LOGIN, SEEDED_LOGINS } from "@/lib/config";

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const loginDemo = useAuthStore((s) => s.loginDemo);
  const javaConn = useConnStore((s) => s.java);

  const [username, setUsername] = useState("vertex");
  const [password, setPassword] = useState("password123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await javaApi.login({ username, password });
      login({ token: res.token, tenantId: res.tenantId, name: res.name, role: res.role });
      router.push("/dashboard");
    } catch (err) {
      const msg = err instanceof JavaApiError ? err.message : "Could not reach the ledger API.";
      setError(`${msg} — you can still explore with a simulated tenant below.`);
    } finally {
      setLoading(false);
    }
  }

  function enterDemo(tenantId: string, name: string, role: "ENTERPRISE" | "ADMIN") {
    loginDemo({ tenantId, name, role });
    router.push("/dashboard");
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div className="pointer-events-none absolute inset-0 [background:radial-gradient(circle_at_50%_0%,color-mix(in_srgb,var(--accent)_12%,transparent),transparent_55%)]" />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-md"
      >
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-accent/10 text-accent">
            <Radio size={20} />
          </div>
          <h1 className="font-display text-xl font-semibold">Sign in to the trading floor</h1>
          <p className="mt-1 text-sm text-muted">SpectraLedger · autonomous 5G spectrum clearinghouse</p>
        </div>

        <Card className="p-6">
          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs uppercase tracking-wide text-muted">Username</label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm font-mono outline-none focus:border-accent/50"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs uppercase tracking-wide text-muted">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm font-mono outline-none focus:border-accent/50"
              />
            </div>
            {error && <p className="text-xs text-warning">{error}</p>}
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Signing in…" : "Sign in"} <ArrowRight size={14} />
            </Button>
          </form>
          <p className="mt-3 text-center text-[11px] text-muted">
            Ledger API: {javaConn === "live" ? <span className="text-success">reachable</span> : <span className="text-accent-2">not reachable — demo tenants below work fully offline</span>}
          </p>
        </Card>

        <div className="mt-6">
          <p className="mb-2 flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted">
            <ShieldCheck size={13} /> Seeded demo tenants
          </p>
          <div className="grid grid-cols-2 gap-2">
            {SEEDED_LOGINS.map((t) => (
              <button
                key={t.username}
                onClick={() => enterDemo(`t-${t.username}`, t.label, "ENTERPRISE")}
                className="rounded-lg border border-border bg-surface px-3 py-2.5 text-left text-sm hover:border-accent/40 hover:bg-white/5 transition-colors"
              >
                <span className="block font-medium">{t.label}</span>
                <span className="text-[11px] text-muted">@{t.username}</span>
              </button>
            ))}
          </div>
          <button
            onClick={() => enterDemo("t-admin", ADMIN_LOGIN.label, "ADMIN")}
            className="mt-2 flex w-full items-center justify-between rounded-lg border border-accent-2/30 bg-accent-2/5 px-3 py-2.5 text-sm hover:bg-accent-2/10 transition-colors"
          >
            <span className="font-medium">{ADMIN_LOGIN.label}</span>
            <Badge tone="accent2">Admin</Badge>
          </button>
        </div>
      </motion.div>
    </div>
  );
}
