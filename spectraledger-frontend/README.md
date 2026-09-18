# SpectraLedger — Frontend

Autonomous 5G spectrum arbitrage & enterprise bandwidth clearinghouse. Next.js 16 (App Router) + TypeScript +
Tailwind v4 + Framer Motion + Zustand, wired against both backend services described in the handoff docs.

## Quick start

```bash
npm install
cp .env.example .env.local   # point at your running backends, or leave as-is for demo mode
npm run dev
```

Open `http://localhost:3000`. Sign in with one of the four seeded Java-backend tenants, or click a demo tenant on
the login screen — demo tenants work with **zero backends running**, see "Demo mode" below.

## Architecture decision: this frontend talks to *both* backends directly

The AI engine doc left one open question: should the frontend go through the Java backend for everything, or hit
the AI engine's own `/ws/stream` directly? The answer implemented here is **both, directly, in parallel**:

- **Java backend** (`NEXT_PUBLIC_JAVA_API_URL`) owns auth, tenants, accounts, the real order book, real trades, and
  the ledger. The frontend calls its REST API (`/api/**`) and subscribes to its STOMP/SockJS `/ws` endpoint
  (`/topic/orderbook`, `/topic/trades`).
- **AI engine** (`NEXT_PUBLIC_AI_API_URL`) owns forecasts, pricing explanations, and agent reasoning — none of
  which the Java backend relays. The frontend calls its REST API (`/forecast`, `/price`, `/agent/evaluate`,
  `/revenue`, `/demo/*`) and connects to its raw WebSocket firehose at `/ws/stream`.

This was the only option that didn't leave a whole category of real, already-built data (telemetry, forecast
confidence, the reasoning feed, the price formula breakdown) unreachable. If the two backends later grow a relay
between them, only `src/lib/api/*` and `src/lib/ws/*` need to change — every component reads from the Zustand
stores in `src/store/*`, not from the transport layer directly.

Java's `/api/orders` wants `pricePerMbpsPerMin`; the AI engine speaks `bid_price`/`ask_price` in USD/Mbps-**hour**.
`src/lib/format.ts` (`hourToMinuteRate` / `minuteToHourRate`) is the single place that conversion happens.

## Demo mode — the app never opens blank

`src/lib/demo/engine.ts` is a self-contained market simulator that mirrors both contracts' exact field names and
shapes. On boot, `AppProviders` races a reachability probe against each backend (4s timeout); whichever one
doesn't answer falls back to the simulator for that half of the app, and the connection dots in the top bar say
so (`LIVE` / `DEMO` / `CONNECTING` / `OFFLINE`) — nothing pretends to be live when it isn't. This matters for a
judged demo: a dropped Wi-Fi connection or a backend that hasn't finished booting should never produce a blank
screen.

The demo ledger's hash chain is not fake data — each entry is a real SHA-256 (Web Crypto) of the previous entry's
hash plus its own fields, so "Verify Ledger Integrity" has something genuine to recompute even fully offline.

## Design decisions worth knowing about

- **Cursor follower**: implemented (`src/components/cursor/CursorFollower.tsx`), but mounted **only on the
  marketing landing page** (`src/app/page.tsx`), never inside the trading terminal. A dense grid of order-book
  rows, ledger entries and small click targets is exactly where a custom cursor competes with the native pointer
  for precision — a real cost on a page whose whole premise is "read fast, click fast." The landing page has no
  such cost, so that's where the motion lives.
- **No blank loading states**: every route has a `loading.tsx` using `LoadingScene` (a signal-acquisition sweep,
  on-brand for a spectrum product) instead of a bare spinner or blank flash. Every data panel (order book, trade
  tape, ledger, telemetry strip, SLA gauge) renders a themed skeleton until its first frame of data arrives,
  live or demo.
- **404 page**: `src/app/not-found.tsx` — a glitching "404" with a flatlining signal waveform ("0 Mbps allocated
  to this route"), tied to the product's own vocabulary instead of a generic error graphic.
- **Numbers never jitter**: every numeric value renders in `font-mono` with `tabular-nums`, so columns of prices
  and quantities stay aligned as the WebSocket updates them.
- **AI vs. human trades are visually distinct**: any trade placed by an autonomous agent carries a small bot glyph
  (trade tape) and renders in the violet accent color instead of cyan (trade network map) — the pitch's strongest
  demo moment is trades clearing with nobody clicking anything, so the UI should make that obvious at a glance.

## Pages

| Route | What it shows |
|---|---|
| `/` | Landing page — live ticker of real/simulated trades, feature grid, how-it-works |
| `/login` | Real JWT login against the Java backend, or one-click seeded/demo tenants |
| `/dashboard` | Trading floor: revenue ticker, live telemetry strip, order book depth, trade network map, trade tape |
| `/agents` | Slice picker, live forecast band + confidence interval, the pricing formula with live numbers, SLA gauge, live agent reasoning feed |
| `/ledger` | Balance/escrow/equity breakdown, double-entry ledger with hash-chain visualization, "Verify Ledger Integrity" |
| `/admin` | Safety-buffer slider + per-tier price floors, with a live illustrative preview of their effect (admin role only) |

## Stack

Next.js 16 App Router · React 19 · TypeScript · Tailwind CSS v4 · Framer Motion · Zustand · `@stomp/stompjs` +
`sockjs-client` (Java backend) · native `WebSocket` (AI engine) · `@fontsource/*` self-hosted fonts (Space
Grotesk / Inter / JetBrains Mono — bundled at build time, no runtime dependency on Google Fonts).

## Known gaps carried over from the backend docs

Mirrored honestly in the UI rather than hidden: single-round price-crossing negotiation (not iterative haggling),
the 2% platform fee is a reporting figure until the AI engine's revenue-skim becomes a real ledger entry, and the
AI engine's own Java-backend field-name assumptions (register/login payloads, JWT field name, trade field names)
are that team's integration detail — this frontend only depends on the contracts documented in the handoff, which
are authoritative.
