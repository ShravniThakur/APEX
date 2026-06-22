"""Central configuration. Reads from backend/.env (never hardcode secrets)."""
import os
from pathlib import Path

from dotenv import load_dotenv

# backend/apex/config.py -> parents[0]=apex, [1]=backend, [2]=repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/apex",
)

CATALOGUE_PATH = Path(
    os.getenv("APEX_CATALOGUE_PATH", str(REPO_ROOT / "product_catalogue.json"))
)

RANDOM_SEED = int(os.getenv("APEX_RANDOM_SEED", "42"))

# Non-prod email sink: if set, ALL outbound Analyser email routes here regardless of
# the customer's stored address (so the demo never emails real third parties).
DEMO_EMAIL = os.getenv("APEX_DEMO_EMAIL")

# Agentic loop — Groq LLM (reasoning narrative + customer message generation).
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")  # voice STT

# Analyser outbound email (Resend). In non-prod ALL mail routes to DEMO_EMAIL.
# Resend's onboarding@resend.dev sender works in test mode to your own account email.
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("APEX_EMAIL_FROM", "APEX (SBI) <onboarding@resend.dev>")

# Public base URL the API is reachable at — used to build click-tracking links in emails.
PUBLIC_URL = os.getenv("APEX_PUBLIC_URL", "http://localhost:8000")
