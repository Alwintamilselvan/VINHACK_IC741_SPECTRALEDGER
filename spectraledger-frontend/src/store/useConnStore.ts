import { create } from "zustand";
import type { ConnState } from "@/lib/types";

interface ConnStore {
  java: ConnState;
  ai: ConnState;
  setJava: (s: ConnState) => void;
  setAi: (s: ConnState) => void;
}

export const useConnStore = create<ConnStore>((set) => ({
  java: "connecting",
  ai: "connecting",
  setJava: (s) => set({ java: s }),
  setAi: (s) => set({ ai: s }),
}));
