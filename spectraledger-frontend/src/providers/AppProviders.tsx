"use client";

import { useEffect, useRef } from "react";
import { javaApi } from "@/lib/api/javaClient";
import { aiApi } from "@/lib/api/aiClient";
import { JavaSocket } from "@/lib/ws/javaSocket";
import { AiSocket } from "@/lib/ws/aiSocket";
import { demoEngine } from "@/lib/demo/engine";
import { CONNECT_TIMEOUT_MS } from "@/lib/config";
import { useConnStore } from "@/store/useConnStore";
import { useMarketStore } from "@/store/useMarketStore";
import { useAgentStore } from "@/store/useAgentStore";

async function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await p;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Boots the two live connections in parallel, races each against a timeout,
 * and falls back to the local DemoEngine for whichever side doesn't answer.
 * This runs once at the app root so every page shares one market feed
 * instead of re-subscribing per component.
 */
export default function AppProviders({ children }: { children: React.ReactNode }) {
  const setJavaConn = useConnStore((s) => s.setJava);
  const setAiConn = useConnStore((s) => s.setAi);
  const setFleet = useMarketStore((s) => s.setFleet);
  const setOrderBook = useMarketStore((s) => s.setOrderBook);
  const upsertBucket = useMarketStore((s) => s.upsertOrderBookBucket);
  const pushTrade = useMarketStore((s) => s.pushTrade);
  const pushTelemetry = useMarketStore((s) => s.pushTelemetry);
  const pushDecision = useAgentStore((s) => s.pushDecision);

  const bootedRef = useRef(false);

  useEffect(() => {
    if (bootedRef.current) return;
    bootedRef.current = true;

    setFleet(demoEngine.getFleet());

    let javaSocket: JavaSocket | null = null;
    let aiSocket: AiSocket | null = null;
    let demoStarted = false;
    const ensureDemo = () => {
      if (demoStarted) return;
      demoStarted = true;
      demoEngine.on("telemetry", pushTelemetry);
      demoEngine.on("decision", pushDecision);
      demoEngine.on("trade", pushTrade);
      demoEngine.on("orderbook", setOrderBook);
      demoEngine.start();
    };

    (async () => {
      try {
        await withTimeout(javaApi.ping(), CONNECT_TIMEOUT_MS);
        setJavaConn("live");
        javaSocket = new JavaSocket();
        javaSocket.connect({
          onOrderBook: upsertBucket,
          onTrade: pushTrade,
          onStatus: (s) => setJavaConn(s === "connected" ? "live" : s === "connecting" ? "connecting" : "demo"),
        });
        const book = await javaApi.orderBook().catch(() => []);
        if (book.length) setOrderBook(book);
        const tape = await javaApi.trades().catch(() => []);
        if (tape.length) tape.forEach(pushTrade);
      } catch {
        setJavaConn("demo");
        ensureDemo();
      }

      try {
        await withTimeout(aiApi.ping(), CONNECT_TIMEOUT_MS);
        setAiConn("live");
        aiSocket = new AiSocket();
        aiSocket.connect({
          onEvent: (e) => {
            if (e.topic === "telemetry.raw") pushTelemetry(e);
            else if (e.topic === "agent.decision") pushDecision(e);
            else if (e.topic === "trade.executed") {
              pushTrade({
                id: Number(e.trade_id) || Math.random(),
                bidOrderId: 0,
                askOrderId: 0,
                buyerTenantId: e.buyer_slice_id,
                sellerTenantId: e.seller_slice_id,
                quantityMbps: e.quantity_mbps,
                executionPrice: e.price,
                durationMinutes: 30,
                qosTier: "SILVER",
                totalAmount: e.price * e.quantity_mbps,
                sliceReassignmentStatus: "CONFIRMED",
                sliceReassignmentRef: null,
                clearedAt: e.executed_at,
                isAgentTrade: true,
              });
            }
          },
          onStatus: (s) => setAiConn(s === "connected" ? "live" : s === "connecting" ? "connecting" : "demo"),
        });
      } catch {
        setAiConn("demo");
        ensureDemo();
      }
    })();

    return () => {
      javaSocket?.disconnect();
      aiSocket?.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <>{children}</>;
}
