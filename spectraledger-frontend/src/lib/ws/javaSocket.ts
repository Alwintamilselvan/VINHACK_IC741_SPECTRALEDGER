import { Client, type IMessage } from "@stomp/stompjs";
import SockJS from "sockjs-client";
import { JAVA_WS_URL } from "@/lib/config";
import type { OrderBookBucket, Trade } from "@/lib/types";

interface JavaSocketCallbacks {
  onOrderBook: (bucket: OrderBookBucket) => void;
  onTrade: (trade: Trade) => void;
  onStatus: (status: "connecting" | "connected" | "disconnected") => void;
}

/**
 * Thin wrapper around STOMP-over-SockJS to the Java backend's /ws endpoint.
 * Subscribes to /topic/orderbook and /topic/trades exactly as documented.
 * No auth is required on the handshake itself.
 */
export class JavaSocket {
  private client: Client | null = null;

  connect(cb: JavaSocketCallbacks) {
    cb.onStatus("connecting");
    const client = new Client({
      webSocketFactory: () => new SockJS(JAVA_WS_URL) as unknown as WebSocket,
      reconnectDelay: 4000,
      heartbeatIncoming: 10000,
      heartbeatOutgoing: 10000,
      onConnect: () => {
        cb.onStatus("connected");
        client.subscribe("/topic/orderbook", (msg: IMessage) => {
          try {
            cb.onOrderBook(JSON.parse(msg.body));
          } catch {
            /* ignore malformed frame */
          }
        });
        client.subscribe("/topic/trades", (msg: IMessage) => {
          try {
            cb.onTrade(JSON.parse(msg.body));
          } catch {
            /* ignore malformed frame */
          }
        });
      },
      onWebSocketClose: () => cb.onStatus("disconnected"),
      onStompError: () => cb.onStatus("disconnected"),
    });
    this.client = client;
    client.activate();
  }

  disconnect() {
    this.client?.deactivate();
    this.client = null;
  }
}
