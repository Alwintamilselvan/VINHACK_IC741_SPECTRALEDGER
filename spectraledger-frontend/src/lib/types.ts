// ---------------------------------------------------------------------------
// Shared types mirroring the two backend contracts exactly.
// Java Spring Boot backend = source of truth for accounts/orders/trades/ledger.
// Python AI Engine = source of truth for forecasts/pricing/agent reasoning.
// ---------------------------------------------------------------------------

export type QosTier = "BRONZE" | "SILVER" | "GOLD" | "PLATINUM";
export type OrderSide = "BID" | "ASK";
export type OrderStatus = "OPEN" | "PARTIALLY_FILLED" | "FILLED" | "CANCELLED";
export type ReassignmentStatus = "PENDING" | "CONFIRMED" | "FAILED";
export type TenantRole = "ENTERPRISE" | "ADMIN";

// --- Java backend: auth -----------------------------------------------------

export interface AuthResponse {
  token: string;
  tenantId: string;
  name: string;
  role: TenantRole;
}

export interface RegisterPayload {
  name: string;
  username: string;
  password: string;
  openingBalance: number;
  initialSliceCapacityMbps: number;
  initialSliceQosTier: QosTier;
}

export interface LoginPayload {
  username: string;
  password: string;
}

// --- Java backend: orders ----------------------------------------------------

export interface OrderPayload {
  sliceId: string;
  side: OrderSide;
  quantityMbps: number;
  pricePerMbpsPerMin: number;
  durationMinutes: number;
  qosTier: QosTier;
}

export interface Trade {
  id: number;
  bidOrderId: number;
  askOrderId: number;
  buyerTenantId: string;
  sellerTenantId: string;
  quantityMbps: number;
  executionPrice: number;
  durationMinutes: number;
  qosTier: QosTier;
  totalAmount: number;
  sliceReassignmentStatus: ReassignmentStatus;
  sliceReassignmentRef: string | null;
  clearedAt: string;
  /** client-side only: true if this trade was placed by an autonomous AI agent, not a human */
  isAgentTrade?: boolean;
}

export interface Order {
  id: number;
  tenantId: string;
  sliceId: string;
  side: OrderSide;
  quantityMbps: number;
  remainingMbps: number;
  pricePerMbpsPerMin: number;
  durationMinutes: number;
  qosTier: QosTier;
  status: OrderStatus;
  createdAt: string;
  immediateFills: Trade[];
}

export interface OrderBookLevel {
  price: number;
  totalQuantityMbps: number;
  orderCount: number;
}

export interface OrderBookBucket {
  qosTier: QosTier;
  durationMinutes: number;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
}

// --- Java backend: accounts & slices -----------------------------------------

export interface Account {
  tenantId: string;
  name: string;
  username: string;
  role: TenantRole;
  balance: number;
  escrowBalance: number;
  totalEquity: number;
}

export interface LedgerEntry {
  id: number;
  tradeId: number;
  entryType: "DEBIT" | "CREDIT";
  amount: number;
  balanceAfter: number;
  description: string;
  entryHash: string;
  previousEntryHash: string;
  createdAt: string;
}

export interface Slice {
  id: string;
  tenantId: string;
  totalCapacityMbps: number;
  allocatedMbps: number;
  availableMbps: number;
  qosTier: QosTier;
}

// --- Java backend: admin ------------------------------------------------------

export interface AdminSettings {
  safetyBufferPercent: number;
  priceFloorBronze: number;
  priceFloorSilver: number;
  priceFloorGold: number;
  priceFloorPlatinum: number;
  updatedAt: string;
}

export interface ChainVerification {
  valid: boolean;
  entriesChecked: number;
  firstBrokenEntryId: number | null;
  message: string;
}

export interface ApiError {
  timestamp: string;
  status: number;
  error: string;
  message: string;
  path: string;
  fieldErrors: unknown[];
}

// --- AI engine ----------------------------------------------------------------

export type SliceType = "eMBB" | "URLLC" | "mMTC" | "AI_TRAINING";
export type AgentRole = "buyer" | "seller";
export type AgentDecision = "list" | "hold" | "buy" | "sell";
export type Trend = "rising" | "falling" | "stable";

export interface ConfidenceInterval {
  lower: number;
  upper: number;
}

export interface ForecastResponse {
  slice_id: string;
  slice_type: SliceType;
  generated_at: string;
  horizon_minutes: number;
  predicted_demand_mbps: number;
  confidence_interval: ConfidenceInterval;
  confidence_score: number;
  trend: Trend;
  model_version: string;
}

export interface PriceComponents {
  base_rate: number;
  congestion_multiplier: number;
  qos_priority_weight: number;
  urgency_factor: number;
}

export interface PriceResponse {
  slice_id: string;
  unit: string;
  bid_price: number;
  ask_price: number;
  mid_price: number;
  confidence_score: number;
  components: PriceComponents;
  explanation: string;
}

export interface AgentDecisionEvent {
  topic: "agent.decision";
  slice_id: string;
  role: AgentRole;
  decision: AgentDecision;
  quantity_mbps: number;
  price: number;
  qos_priority?: string;
  reasoning: string;
  sla_gate_passed: boolean;
  decided_at: string;
  matched_order_id?: string | null;
}

export interface TelemetryRawEvent {
  topic: "telemetry.raw";
  slice_id: string;
  timestamp: string;
  throughput_mbps: number;
  latency_ms: number;
}

export interface TradeExecutedEvent {
  topic: "trade.executed";
  trade_id: string;
  buyer_slice_id: string;
  seller_slice_id: string;
  price: number;
  quantity_mbps: number;
  executed_at: string;
}

export type AiStreamEvent = AgentDecisionEvent | TelemetryRawEvent | TradeExecutedEvent;

export interface RevenueSummary {
  trade_count: number;
  total_notional_volume: number;
  total_fees_collected: number;
}

export interface RevenueTrade {
  trade_id: string;
  fee: number;
  notional: number;
  collected_at: string;
}

export interface DemoSlice {
  slice_id: string;
  slice_type: SliceType;
  capacity_mbps: number;
  role: string;
  base_utilization_pct: number;
}

// --- Client-side connection status ------------------------------------------

export type ConnState = "connecting" | "live" | "demo" | "offline";
