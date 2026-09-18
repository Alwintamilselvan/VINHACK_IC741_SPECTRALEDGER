import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { TenantRole } from "@/lib/types";

interface AuthStore {
  token: string | null;
  tenantId: string | null;
  name: string | null;
  role: TenantRole | null;
  demoLoggedIn: boolean;
  login: (a: { token: string; tenantId: string; name: string; role: TenantRole }) => void;
  loginDemo: (a: { tenantId: string; name: string; role: TenantRole }) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      tenantId: null,
      name: null,
      role: null,
      demoLoggedIn: false,
      login: ({ token, tenantId, name, role }) => set({ token, tenantId, name, role, demoLoggedIn: false }),
      loginDemo: ({ tenantId, name, role }) => set({ token: null, tenantId, name, role, demoLoggedIn: true }),
      logout: () => set({ token: null, tenantId: null, name: null, role: null, demoLoggedIn: false }),
    }),
    {
      name: "spectraledger-auth",
      storage: createJSONStorage(() => (typeof window !== "undefined" ? localStorage : ({} as Storage))),
    }
  )
);
