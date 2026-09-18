"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { useAuthStore } from "@/store/useAuthStore";
import { useAccount } from "@/hooks/useAccount";

export default function AppShellLayout({ children }: { children: React.ReactNode }) {
  const tenantId = useAuthStore((s) => s.tenantId);
  const router = useRouter();
  useAccount();

  useEffect(() => {
    if (!tenantId) router.replace("/login");
  }, [tenantId, router]);

  if (!tenantId) return null;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-x-hidden px-4 py-5 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
