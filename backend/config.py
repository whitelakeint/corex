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
