"""
SpectraLedger AI Engine -- FastAPI entry point.

Run locally:
    uvicorn app.main:app --reload --port 8000

See README.md for full endpoint docs and sample payloads.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import agent, demo, events, forecast, orderbook, price, revenue, ws
from app.services.autonomous import start_autonomous_loop, stop_autonomous_loop
from app.services.backend_trade_poller import start_backend_poller, stop_backend_poller
from app.services.broadcast import start_live_feed, stop_live_feed
from app.services.forecasting import ensure_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("spectraledger.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Ensuring forecast model is trained/loaded...")
    ensure_model()
    logger.info("Starting live telemetry simulator (fallback demo feed)...")
    start_live_feed()
    logger.info("Starting autonomous market-maker loop...")
    start_autonomous_loop()
    logger.info("Starting Java backend trade poller (no-op if JAVA_BACKEND_BASE_URL is unset)...")
    start_backend_poller()
    yield
    stop_backend_poller()
    stop_autonomous_loop()
    stop_live_feed()


app = FastAPI(
    title="SpectraLedger AI Engine",
    description=(
        "Forecasting, dynamic pricing, and autonomous LangGraph trading agents "
        "for an autonomous B2B clearinghouse that turns private 5G network "
        "slices into tradeable bandwidth. This service owns /forecast, /price, "
        "/agent/evaluate, a persistent cross-slice /orderbook, a background "
        "market-maker loop that trades on its own with zero external calls, "
        "an outbound trade webhook to the Java backend, and the "
        "telemetry/trade/decision event stream at /ws/stream -- see README.md."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon demo: wide open so the Next.js frontend can hit this directly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast.router)
app.include_router(price.router)
app.include_router(agent.router)
app.include_router(orderbook.router)
app.include_router(revenue.router)
app.include_router(ws.router)
app.include_router(events.router)
app.include_router(demo.router)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "service": "spectraledger-ai-engine"}


@app.get("/", tags=["meta"])
async def root():
    return {
        "service": "SpectraLedger AI Engine",
        "docs": "/docs",
        "endpoints": ["/forecast", "/price", "/agent/evaluate", "/ws/stream", "/events/{topic}", "/demo/slices", "/demo/telemetry/{slice_id}"],
    }