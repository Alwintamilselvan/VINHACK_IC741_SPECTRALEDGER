# SpectraLedger — Core Banking Engine

Backend for SpectraLedger, a real-time B2B spot market for trading idle private 5G network
slice bandwidth. This service owns multi-tenant accounts, the order book, the matching engine,
and the double-entry ledger. Built for Vinhack '26 (VIT Vellore, Sept 18–19).

## Stack, and why

Spring Boot 3.3 / Java 21 (virtual threads enabled) / Spring MVC / Spring Data JPA / PostgreSQL
16 / Spring Security (JWT) / STOMP over WebSocket. No Kafka, no Redis — see the "what we
deliberately didn't build" section below for why, and what the fallback is.

## Prerequisites

- JDK 21, Maven (or the wrapper), Docker Desktop.

## Running it

```bash
docker compose up -d          # starts Postgres on localhost:5432
./mvnw spring-boot:run        # or run CoreBankingEngineApplication from VS Code
curl http://localhost:8080/actuator/health   # -> {"status":"UP"}
```

On first run, `DataSeeder` populates 1 admin + 4 enterprise tenants, 5 network slices, platform
settings (safety buffer + per-tier price floors), and a handful of already-cleared trades plus a
few resting orders, so the dashboard never opens empty. It only runs once (skipped automatically
once the `tenants` table is non-empty).

Seeded enterprise logins (password `password123`): `vertex`, `aurora`, `helios`, `nimbus`.
Seeded admin login: username `admin`, password `admin123`.

### The Windows timezone fix, if you're wondering why it's there

`CoreBankingEngineApplication.main()` force-sets the JVM's default timezone to `Asia/Kolkata`
before Spring starts. On Windows, the JVM can resolve its default timezone to the legacy alias
`Asia/Calcutta` (from the OS's "India Standard Time" mapping), and PostgreSQL's JDBC driver
sends that name to the server at connection time. Recent PostgreSQL builds (particularly the
Windows installer's bundled tzdata) reject that legacy name outright with `FATAL: invalid value
for parameter "TimeZone"`, which aborts the whole Spring context before Tomcat can serve
anything. Setting it explicitly in code means the fix applies identically for every teammate,
regardless of OS locale or how they launch the app.

## API contract

All endpoints except `/api/auth/**`, `/actuator/**` and the WebSocket handshake require
`Authorization: Bearer <jwt>`. The authenticated tenant is always read from the token's `sub`
claim — never from a request body — so a tenant can only ever act as itself.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Create a new enterprise tenant + its first slice. Returns a JWT. |
| POST | `/api/auth/login` | Returns a JWT for an existing tenant. |
| POST | `/api/orders` | Submit a bid or ask. Matches immediately against the book; response includes any immediate fills. This is what the AI teammate's trading agents call. |
| DELETE | `/api/orders/{id}` | Cancel a resting order; releases escrow or slice capacity. |
| GET | `/api/orders/me` | The caller's own order history. |
| GET | `/api/orders/book` | Full live order book, every active (QoS, duration) bucket. |
| GET | `/api/orders/book/{qosTier}/{durationMinutes}` | One bucket's book. |
| POST | `/api/slices` | Add another network slice to the caller's own account. |
| GET | `/api/accounts/me` | Balance, escrow balance, total equity. |
| GET | `/api/accounts/me/ledger` | The caller's full double-entry ledger history. |
| GET | `/api/accounts/me/slices` | The caller's slices and their available capacity. |
| GET | `/api/trades` | Public trade tape — last 50 cleared trades, market-wide. |
| GET | `/api/trades/me` | The caller's own trade history (as buyer or seller). |
| GET | `/api/admin/settings` | *(ADMIN only)* Current safety-buffer % and per-QoS-tier price floors. |
| PUT | `/api/admin/settings` | *(ADMIN only)* Update them. Enforced immediately on the next order submitted, inside the same locked transaction as capacity reservation. |
| GET | `/api/admin/ledger/verify-chain` | *(ADMIN only)* Recomputes the ledger's hash chain from genesis and reports whether it's intact — see below. |

### WebSocket

Connect (SockJS-compatible) to `ws://localhost:8080/ws`, then subscribe to:

- `/topic/orderbook` — a full bucket snapshot (`OrderBookBucketResponse`), pushed every time any order in that bucket changes.
- `/topic/trades` — each cleared trade (`TradeResponse`), pushed the instant its settlement transaction commits, and pushed again when its mocked slice-reassignment status flips from `PENDING` to `CONFIRMED`/`FAILED`.

## The ledger's consistency guarantee, in plain English

Every trade moves money between exactly two tenants: the buyer and the seller. The entire
operation — checking both balances, updating both of them, writing the trade record, and
writing the two ledger lines that describe it — happens inside a single database transaction
(`TradeSettlementService.settle`). Postgres either applies every one of those writes or none of
them; there's no state where a trade is half-recorded.

Before either balance can be touched, the code takes an explicit row-level lock on both
tenants (`SELECT ... FOR UPDATE`, via Hibernate's `PESSIMISTIC_WRITE`) for the entire duration
of that transaction. That means if two trades try to touch the same account at the same
instant, the second one physically waits at the database level until the first one finishes —
they cannot interleave their reads and writes, which is exactly the mechanism that prevents a
lost update (the classic "read 100, read 100, both subtract 60, balance is now 40 instead of
-20 rejected" bug). The two locks are always taken in the same order — the tenant with the
smaller UUID first, regardless of who's buying or selling — which is what stops two concurrent
trades between the same pair of tenants from deadlocking each other.

On top of that, every trade produces exactly one debit and one credit of the identical amount,
checked in code before the transaction is allowed to commit. That's what makes this a real
double-entry ledger and not just an activity log: you can sum every ledger line ever written and
the signed total is always zero.

`src/test/java/.../ConcurrentBidReservationTest.java` proves this isn't just a claim: it fires
30 concurrent bid requests against a single account that can only afford 10, and asserts that
exactly 10 succeed, the rest are cleanly rejected, and the account's balance is never negative
and never loses or gains a cent it shouldn't.

## The tamper-evident audit trail

Every `LedgerEntry` also carries `entryHash` and `previousEntryHash`. Each new entry's hash is
computed from its own data (tenant, trade, type, amount, balance-after, description) plus the
hash of the entry immediately before it, chained across the *entire* ledger table, not just per
tenant. Appending to the chain locks a single singleton row (`LedgerChainState`) first, which is
what forces the chain to stay a straight line even when unrelated trades are settling
concurrently — without that lock, two trades for different tenant pairs could both read the same
"current tip" and each append believing they extended it, silently forking the chain.

`GET /api/admin/ledger/verify-chain` recomputes every hash from the raw stored values and
reports the first entry where it no longer matches — the honest answer to "how do you know
nobody edited a row directly in the database": you don't have to trust that no one did, you can
prove it on demand.

## Platform risk controls (safety buffer + price floors)

An ADMIN sets a global safety-buffer percentage (the fraction of every slice's total capacity
that can never be listed for sale, regardless of how idle the forecasting engine thinks it is)
and a minimum ask price per QoS tier. Both are enforced inside `OrderService#submitOrder`, in
the same locked transaction as the ASK's capacity reservation — an enterprise (or a buggy
trading agent) cannot list bandwidth below the floor or past the buffer no matter what the
frontend sends, because the backend re-checks it server-side every time regardless of what the
UI already validated.

## What we deliberately didn't build, and why

- **Kafka.** A real event stream would have cost 3–5 hours of setup risk for marginal extra
  credibility over what we did build: Spring's own `ApplicationEventPublisher` with
  `@TransactionalEventListener(phase = AFTER_COMMIT)`, which gives the same decoupling (trade
  settlement doesn't know or care who's listening) with zero extra infrastructure to
  misconfigure during a live demo. Swapping in a real broker later is a listener change, not a
  rearchitecture.
- **Redis.** At this scale (a handful of tenants, one JVM instance, no need to share order-book
  state across processes), an in-memory `TreeMap`-per-bucket structure is faster to build,
  faster to run, and just as defensible as a cache would be. Postgres remains the system of
  record; the in-memory book is rebuilt from it on every startup.
- **Real NSSF/RAN integration.** No 5G core network exists for this hackathon.
  `SliceReassignmentService` mocks that call honestly — async, realistic latency, occasional
  simulated failure — and we say so directly if asked. Crucially, it only ever runs *after* the
  ledger transaction has already committed, so nothing about the mocked network call can affect
  the correctness of the money or capacity accounting.
- **Kafka and Redis remain the only two deliberate omissions** — everything else in the original
  Tier 0/1/2 feature list (matching engine, ledger, WebSocket push, admin controls, tamper-
  evident audit trail, mocked slice reassignment) is built and wired.

## Manual verification checklist

1. `docker compose up -d && ./mvnw spring-boot:run` — confirm `/actuator/health` returns UP and
   the log shows the seed step completing with 4 tenants.
2. `./mvnw test -Dtest=ConcurrentBidReservationTest` (Postgres must be running) — confirm it
   passes: exactly 10 of 30 concurrent bids succeed, final balance is exactly accounted for.
3. Log in as `vertex` and `aurora` (`POST /api/auth/login`). Have `vertex` submit an ASK on its
   GOLD slice, then `aurora` submit a crossing BID from a different terminal/Postman tab at the
   same moment — confirm exactly one trade clears, both balances update correctly, and the
   ledger for both tenants shows matching debit/credit lines referencing the same trade id.
4. Subscribe to `/ws` from a WebSocket client (or the frontend) before step 3 and confirm the
   order book and trade tape update live, with no polling.
5. Watch a cleared trade's `sliceReassignmentStatus` in the trade tape flip from `PENDING` to
   `CONFIRMED` roughly half a second later, without any client action.
6. Try to submit a BID larger than the tenant's balance can cover — confirm a `409` with a clear
   `InsufficientBalanceException` message, and that no partial state was written.
7. Log in as `admin`, `GET /api/admin/ledger/verify-chain` — confirm `valid: true` after the
   seeded trades. Then, purely to prove the point, connect to Postgres directly and run
   `UPDATE ledger_entries SET balance_after = 999999 WHERE id = 1;`, call verify-chain again, and
   confirm it now reports `valid: false` with `firstBrokenEntryId: 1`.
8. As `admin`, `PUT /api/admin/settings` with a price floor above what an enterprise is about to
   ask for — confirm their next `POST /api/orders` ASK is rejected with `409
   PriceBelowFloorException`, even though nothing on the client changed.
