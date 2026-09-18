"use client";

import { useEffect } from "react";
import { javaApi } from "@/lib/api/javaClient";
import { demoEngine } from "@/lib/demo/engine";
import { useAuthStore } from "@/store/useAuthStore";
import { useAccountStore } from "@/store/useAccountStore";
import { useConnStore } from "@/store/useConnStore";

/**
 * Loads (and live-updates) account, slices, ledger, my-trades and admin
 * settings for whoever is currently logged in — real JWT session against
 * the Java backend, or a picked demo tenant against the DemoEngine.
 */
export function useAccount() {
  const { token, tenantId, role, demoLoggedIn } = useAuthStore();
  const javaConn = useConnStore((s) => s.java);
  const setAccount = useAccountStore((s) => s.setAccount);
  const setSlices = useAccountStore((s) => s.setSlices);
  const setLedger = useAccountStore((s) => s.setLedger);
  const appendLedger = useAccountStore((s) => s.appendLedger);
  const setMyTrades = useAccountStore((s) => s.setMyTrades);
  const setAdminSettings = useAccountStore((s) => s.setAdminSettings);

  useEffect(() => {
    if (!tenantId) return;

    if (token && javaConn === "live") {
      javaApi.myAccount(token).then(setAccount).catch(() => {});
      javaApi.mySlices(token).then(setSlices).catch(() => {});
      javaApi.myLedger(token).then(setLedger).catch(() => {});
      javaApi.myTrades(token).then(setMyTrades).catch(() => {});
      if (role === "ADMIN") javaApi.adminSettings(token).then(setAdminSettings).catch(() => {});
      return;
    }

    if (demoLoggedIn) {
      setAccount(demoEngine.getAccount(tenantId));
      setSlices(demoEngine.getSlices(tenantId));
      setLedger(demoEngine.getLedger(tenantId));
      setAdminSettings(demoEngine.getAdmin());
      const offAcc = demoEngine.on("account", (tid, acc) => {
        if (tid === tenantId) setAccount(acc);
      });
      const offLedger = demoEngine.on("ledger", (tid, entry) => {
        if (tid === tenantId) appendLedger(entry);
      });
      const offTrade = demoEngine.on("trade", () => {
        setSlices(demoEngine.getSlices(tenantId));
        setMyTrades(demoEngine.trades.filter((t) => t.buyerTenantId === tenantId || t.sellerTenantId === tenantId));
      });
      return () => {
        offAcc();
        offLedger();
        offTrade();
      };
    }
  }, [token, tenantId, role, demoLoggedIn, javaConn, setAccount, setSlices, setLedger, appendLedger, setMyTrades, setAdminSettings]);
}
