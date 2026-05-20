import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

TAVUS_API_KEY: str = os.getenv("TAVUS_API_KEY", "")
TAVUS_PERSONA_ID: str = os.getenv("TAVUS_PERSONA_ID", "")
TAVUS_REPLICA_ID: str = os.getenv("TAVUS_REPLICA_ID", "r1af76e94d00")
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8001")
JITSI_BASE_URL: str = os.getenv("JITSI_BASE_URL", "https://meet.whitelakedigital.com")

# Admin session configuration
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "meridian")
