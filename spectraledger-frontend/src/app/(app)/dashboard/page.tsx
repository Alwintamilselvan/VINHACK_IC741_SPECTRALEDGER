import { RevenueTicker } from "@/components/trading/RevenueTicker";
import { TelemetryStrip } from "@/components/trading/TelemetryStrip";
import { OrderBookDepth } from "@/components/trading/OrderBookDepth";
import { TradeTape } from "@/components/trading/TradeTape";
import { TradeNetworkMap } from "@/components/trading/TradeNetworkMap";

export default function DashboardPage() {
  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <div>
        <h1 className="font-display text-2xl font-semibold">Trading floor</h1>
        <p className="text-sm text-muted">Nothing here is scripted — watch it clear on its own.</p>
      </div>

      <RevenueTicker />
      <TelemetryStrip />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <OrderBookDepth />
        </div>
        <TradeNetworkMap />
      </div>

      <div className="h-[420px]">
        <TradeTape />
      </div>
    </div>
  );
}
