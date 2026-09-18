import { create } from "zustand";
import type { Account, AdminSettings, LedgerEntry, Slice, Trade } from "@/lib/types";

interface AccountStore {
  account: Account | null;
  slices: Slice[];
  ledger: LedgerEntry[];
  myTrades: Trade[];
  adminSettings: AdminSettings | null;
  setAccount: (a: Account) => void;
  setSlices: (s: Slice[]) => void;
  setLedger: (l: LedgerEntry[]) => void;
  appendLedger: (e: LedgerEntry) => void;
  setMyTrades: (t: Trade[]) => void;
  setAdminSettings: (a: AdminSettings) => void;
  reset: () => void;
}

export const useAccountStore = create<AccountStore>((set) => ({
  account: null,
  slices: [],
  ledger: [],
  myTrades: [],
  adminSettings: null,
  setAccount: (account) => set({ account }),
  setSlices: (slices) => set({ slices }),
  setLedger: (ledger) => set({ ledger }),
  appendLedger: (e) => set((s) => ({ ledger: [...s.ledger, e] })),
  setMyTrades: (myTrades) => set({ myTrades }),
  setAdminSettings: (adminSettings) => set({ adminSettings }),
  reset: () => set({ account: null, slices: [], ledger: [], myTrades: [], adminSettings: null }),
}));
