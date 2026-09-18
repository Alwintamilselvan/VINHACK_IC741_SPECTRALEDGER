"""
Central, tweakable constants for the demo. Nothing here is a secret --
it's all knobs for the pricing formula, SLA gate, and model paths so
judges/teammates can see and tune the whole system in one place.
"""
import os

# --- Paths -----------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
MODEL_DIR = os.path.join(APP_DIR, "models")
TELEMETRY_CSV = os.path.join(DATA_DIR, "synthetic_telemetry.csv")
FORECAST_MODEL_PATH = os.path.join(MODEL_DIR, "forecast_model.joblib")

MODEL_VERSION = "lightgbm-v1"

# --- Pricing formula ---------------------------------------------------------
# price = base_rate * congestion_multiplier * qos_priority_weight * urgency_factor
DEFAULT_BASE_RATE = 0.05  # USD per Mbps-hour

QOS_PRIORITY_WEIGHTS = {
    "gold": 1.2,
    "silver": 1.0,
    "bronze": 0.85,
}

# Spread applied around the mid price to produce bid/ask (kept small & symmetric for demo clarity)
BID_ASK_SPREAD_PCT = 0.05

# Congestion multiplier bounds (clamped so a runaway forecast can't blow up the price)
CONGESTION_MULTIPLIER_MIN = 0.6
CONGESTION_MULTIPLIER_MAX = 3.0

# Urgency factor bounds. Urgency scales with how soon a forecasted surplus window closes --
# i.e. how little time remains at the requested horizon before demand is expected to consume
# the available surplus.
URGENCY_FACTOR_MIN = 1.0
URGENCY_FACTOR_MAX = 2.0

# --- SLA risk evaluator ------------------------------------------------------
# Fallback / global default confidence threshold. A per-slice override can be
# supplied via SliceState.sla_min_confidence; this is the floor used when a
# slice doesn't specify one, and the value used until/unless a classifier
# upgrade replaces the threshold check.
DEFAULT_SLA_MIN_CONFIDENCE = 0.5

# Safety buffer: Seller Agent will not list bandwidth if doing so would push
# projected utilization above this fraction of capacity.
SLA_MAX_UTILIZATION_AFTER_LISTING = 0.9

# --- Synthetic telemetry generator ------------------------------------------
TELEMETRY_SAMPLE_INTERVAL_MINUTES = 5
DEFAULT_SIM_DAYS = 14

# --- Autonomous market-maker loop --------------------------------------------
# How often (real seconds) the background loop re-evaluates every demo slice
# as both a potential seller and buyer against the live telemetry feed +
# shared order book, with zero external API calls needed. Override via env
# var if you want a faster/slower demo cadence.
AUTONOMOUS_LOOP_TICK_SECONDS = float(os.environ.get("AUTONOMOUS_LOOP_TICK_SECONDS", "8"))

# --- Outbound webhook to the Java backend -----------------------------------
# When a trade clears (from /agent/evaluate or the autonomous loop), POST the
# TradeExecutedEvent payload here, e.g. http://localhost:8080/api/trades/execute.
# Left empty by default -- unset/blank means "no backend to call yet", and
# delivery attempts are skipped (logged, not raised) rather than failing the
# request. Set this once the Java backend's endpoint is up.
BACKEND_TRADE_WEBHOOK_URL = os.environ.get("BACKEND_TRADE_WEBHOOK_URL", "").strip()
WEBHOOK_TIMEOUT_SECONDS = float(os.environ.get("WEBHOOK_TIMEOUT_SECONDS", "5"))

# --- Java backend integration (live order submission) ------------------------
# When set, the autonomous market-maker loop submits real orders to the Java
# backend's own order-book API (POST /api/orders) instead of only matching
# against the AI engine's in-memory book, and observes fills by polling
# GET /api/trades/me instead of relying on an inbound webhook. Left blank
# (the default) means "local-only mode" -- the original self-contained demo
# path stays fully intact, and it's also the automatic fallback for any tick
# where the backend is configured but unreachable (see
# app/services/trade_settlement.py).
JAVA_BACKEND_BASE_URL = os.environ.get("JAVA_BACKEND_BASE_URL", "").strip().rstrip("/")
JAVA_BACKEND_TIMEOUT_SECONDS = float(os.environ.get("JAVA_BACKEND_TIMEOUT_SECONDS", "5"))
# How often (real seconds) to poll GET /api/trades/me per demo company for
# fills, when JAVA_BACKEND_BASE_URL is configured.
JAVA_BACKEND_POLL_SECONDS = float(os.environ.get("JAVA_BACKEND_POLL_SECONDS", "5"))
# Demo login credentials used once per synthetic company (DEFAULT_PROFILES
# entry) on first contact with a fresh backend -- each becomes its own
# registered tenant. On every later run the same slice_id + password logs
# back in instead of re-registering.
JAVA_BACKEND_DEMO_PASSWORD = os.environ.get("JAVA_BACKEND_DEMO_PASSWORD", "Demo123!")
# How long a lease we request per submitted order. The real backend's
# /api/orders takes durationMinutes explicitly; this mirrors the demo's
# default forecast horizon rather than inventing a separate number.
JAVA_BACKEND_ORDER_DURATION_MINUTES = int(os.environ.get("JAVA_BACKEND_ORDER_DURATION_MINUTES", "30"))