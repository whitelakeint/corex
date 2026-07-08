import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

TAVUS_API_KEY: str = os.getenv("TAVUS_API_KEY", "")
TAVUS_PERSONA_ID: str = os.getenv("TAVUS_PERSONA_ID", "")
TAVUS_REPLICA_ID: str = os.getenv("TAVUS_REPLICA_ID", "r1af76e94d00")
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8001")
JITSI_BASE_URL: str = os.getenv("JITSI_BASE_URL", "https://meet.whitelakedigital.com")


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


# --- Kiosk / presence-gating -------------------------------------------------
# KIOSK_MODE: the portal runs presence-driven (attract loop until the controller
# opens a room over the local WebSocket). Implies skipping the login screen.
KIOSK_MODE: bool = _as_bool(os.getenv("KIOSK_MODE", "false"))
# SKIP_LOGIN: bypass the login gate even outside full kiosk mode.
SKIP_LOGIN: bool = _as_bool(os.getenv("SKIP_LOGIN", "false")) or KIOSK_MODE
# Property is fixed by env/config instead of a login-time selection.
PROPERTY_NAME: str = os.getenv("PROPERTY_NAME", "The Meridian")
# Local WebSocket the browser connects to for controller commands.
KIOSK_WS_URL: str = os.getenv("KIOSK_WS_URL", "ws://127.0.0.1:8765")

# --- Bot identity (multi-tenant) --------------------------------------------
# Each physical deployment is pinned to ONE bot/site via config. Every
# conversation, transcript and unanswered question captured by this instance is
# tagged with this slug so the Laravel admin can tell which bot had the problem.
BOT_ID: str = os.getenv("BOT_ID", "default")
BOT_NAME: str = os.getenv("BOT_NAME", PROPERTY_NAME)

# --- Transcript / knowledge-base database (shared with the Laravel admin) ----
# Points at the same MySQL database the Laravel admin manages. Default targets a
# local XAMPP MySQL (root / no password). Capture degrades gracefully (logs a
# warning, never breaks a webhook) if the DB is unreachable.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:@127.0.0.1:3306/corex?charset=utf8mb4",
)
# Set false to disable all DB writes (e.g. a kiosk with no DB access).
CAPTURE_ENABLED: bool = _as_bool(os.getenv("CAPTURE_ENABLED", "true"))
