import { AI_WS_URL } from "@/lib/config";
import type { AiStreamEvent } from "@/lib/types";

interface AiSocketCallbacks {
  onEvent: (e: AiStreamEvent) => void;
  onStatus: (status: "connecting" | "connected" | "disconnected") => void;
}

/**
 * Raw WebSocket client for the AI engine's single-socket firehose
 * (/ws/stream), which carries all three topics — telemetry.raw,
 * agent.decision, trade.executed — tagged by a `topic` field on each frame.
 */
export class AiSocket {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closedByUser = false;

  connect(cb: AiSocketCallbacks) {
    this.closedByUser = false;
    cb.onStatus("connecting");
    try {
      const ws = new WebSocket(AI_WS_URL);
      this.ws = ws;
      ws.onopen = () => cb.onStatus("connected");
      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data) as AiStreamEvent;
          cb.onEvent(data);
        } catch {
          /* ignore malformed frame */
        }
      };
      ws.onclose = () => {
        cb.onStatus("disconnected");
        if (!this.closedByUser) {
          this.reconnectTimer = setTimeout(() => this.connect(cb), 4000);
        }
      };
      ws.onerror = () => ws.close();
    } catch {
      cb.onStatus("disconnected");
    }
  }

  disconnect() {
    this.closedByUser = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }
}
