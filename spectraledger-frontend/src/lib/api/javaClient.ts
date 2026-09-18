import { JAVA_API_URL } from "@/lib/config";
import type {
  Account,
  AdminSettings,
  ApiError,
  AuthResponse,
  ChainVerification,
  LedgerEntry,
  LoginPayload,
  Order,
  OrderBookBucket,
  OrderPayload,
  QosTier,
  RegisterPayload,
  Slice,
  Trade,
} from "@/lib/types";

export class JavaApiError extends Error {
  status: number;
  payload: ApiError | null;
  constructor(message: string, status: number, payload: ApiError | null) {
    super(message);
    this.name = "JavaApiError";
    this.status = status;
    this.payload = payload;
  }
}

interface RequestOpts {
  method?: string;
  body?: unknown;
  token?: string | null;
  signal?: AbortSignal;
}

async function request<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;

  const res = await fetch(`${JAVA_API_URL}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  });

  if (!res.ok) {
    let payload: ApiError | null = null;
    try {
      payload = await res.json();
    } catch {
      /* body wasn't JSON */
    }
    throw new JavaApiError(payload?.message ?? `Request failed (${res.status})`, res.status, payload);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const javaApi = {
  // --- auth ---
  register: (payload: RegisterPayload) =>
    request<AuthResponse>("/api/auth/register", { method: "POST", body: payload }),
  login: (payload: LoginPayload) =>
    request<AuthResponse>("/api/auth/login", { method: "POST", body: payload }),

  // --- orders ---
  submitOrder: (token: string, payload: OrderPayload) =>
    request<Order>("/api/orders", { method: "POST", body: payload, token }),
  cancelOrder: (token: string, orderId: number) =>
    request<Order>(`/api/orders/${orderId}`, { method: "DELETE", token }),
  myOrders: (token: string) => request<Order[]>("/api/orders/me", { token }),
  orderBook: (token?: string | null) => request<OrderBookBucket[]>("/api/orders/book", { token }),
  orderBookBucket: (qosTier: QosTier, durationMinutes: number, token?: string | null) =>
    request<OrderBookBucket>(`/api/orders/book/${qosTier}/${durationMinutes}`, { token }),

  // --- slices ---
  createSlice: (token: string, payload: { totalCapacityMbps: number; qosTier: QosTier }) =>
    request<Slice>("/api/slices", { method: "POST", body: payload, token }),
  mySlices: (token: string) => request<Slice[]>("/api/accounts/me/slices", { token }),

  // --- accounts ---
  myAccount: (token: string) => request<Account>("/api/accounts/me", { token }),
  myLedger: (token: string) => request<LedgerEntry[]>("/api/accounts/me/ledger", { token }),

  // --- trades ---
  trades: (token?: string | null) => request<Trade[]>("/api/trades", { token }),
  myTrades: (token: string) => request<Trade[]>("/api/trades/me", { token }),

  // --- admin ---
  adminSettings: (token: string) => request<AdminSettings>("/api/admin/settings", { token }),
  updateAdminSettings: (token: string, payload: Partial<AdminSettings>) =>
    request<AdminSettings>("/api/admin/settings", { method: "PUT", body: payload, token }),
  verifyChain: (token: string) =>
    request<ChainVerification>("/api/admin/ledger/verify-chain", { token }),

  /** lightweight reachability probe used to decide live vs. demo mode */
  ping: (signal?: AbortSignal) => request<unknown>("/api/trades", { signal }),
};
