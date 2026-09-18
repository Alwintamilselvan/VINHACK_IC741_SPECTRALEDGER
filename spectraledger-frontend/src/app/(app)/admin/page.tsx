"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { RiskControls } from "@/components/admin/RiskControls";
import { RevenueTicker } from "@/components/trading/RevenueTicker";
import { useAuthStore } from "@/store/useAuthStore";

export default function AdminPage() {
  const role = useAuthStore((s) => s.role);
  const router = useRouter();

  useEffect(() => {
    if (role && role !== "ADMIN") router.replace("/dashboard");
  }, [role, router]);

  if (role !== "ADMIN") return null;

  return (
    <div className="mx-auto max-w-[900px] space-y-5">
      <div>
        <h1 className="font-display text-2xl font-semibold">Risk admin</h1>
        <p className="text-sm text-muted">Safety buffers and per-tier price floors for the whole exchange.</p>
      </div>
      <RevenueTicker />
      <RiskControls />
    </div>
  );
}
