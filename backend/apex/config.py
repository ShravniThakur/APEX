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

# ── LLM provider ─────────────────────────────────────────────────────────────
# "groq"   → hosted Groq inference (fast, but the free tier rate-limits after a few calls).
# "ollama" → fully local, OpenAI-compatible Ollama server: no key, no rate limits.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

# Agentic loop — Groq LLM (reasoning narrative + customer message generation).
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")  # voice STT

# Local Ollama (OpenAI-compatible endpoint at /v1). The chat model MUST support tool-calling
# for Guide/Concierge — qwen2.5 and llama3.1 do. Pull one first: `ollama pull qwen2.5:7b`.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# Local Whisper (in-process faster-whisper) — used for voice STT when LLM_PROVIDER == "ollama".
# Sizes: tiny / base / small / medium / large-v3 (bigger = more accurate, slower, more RAM).
LOCAL_WHISPER_MODEL = os.getenv("LOCAL_WHISPER_MODEL", "base")

# Resolved from the provider so the agent call sites stay provider-agnostic.
_USE_OLLAMA = LLM_PROVIDER == "ollama"
CHAT_MODEL = OLLAMA_MODEL if _USE_OLLAMA else GROQ_MODEL
USE_LOCAL_WHISPER = _USE_OLLAMA  # local STT rides along with the local LLM stack
# True when the chat LLM is usable: local Ollama needs no key; hosted Groq needs one.
LLM_READY = _USE_OLLAMA or bool(GROQ_API_KEY)

# Analyser outbound email (Resend). In non-prod ALL mail routes to DEMO_EMAIL.
# Resend's onboarding@resend.dev sender works in test mode to your own account email.
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("APEX_EMAIL_FROM", "APEX (SBI) <onboarding@resend.dev>")

# Public base URL the API is reachable at — used to build click-tracking links in emails.
PUBLIC_URL = os.getenv("APEX_PUBLIC_URL", "http://localhost:8000")
