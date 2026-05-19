import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")
TEMP_DIR = BASE_DIR / "temp"
OUTPUTS_DIR = BASE_DIR / "outputs"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ── OpenRouter model config ──────────────────────────────────────────────────
PRIMARY_MODEL = "google/gemini-2.5-flash"
FALLBACK_MODEL = "qwen/qwen3-32b"

CAPTION_FONT = "Arial"
CAPTION_FONT_SIZE = 22
CAPTION_OUTLINE_WIDTH = 3

# ── Clip cutting ────────────────────────────────────────────────────────────
TAIL_PAD_MS = 300

# ── Ranking ─────────────────────────────────────────────────────────────────
MIN_STANDALONE_SCORE = 40
DIVERSITY_MIN_GAP_S = 60.0
TRANSCRIPT_OVERLAP_THRESHOLD = 0.50

# ── Hook-first ──────────────────────────────────────────────────────────────
HOOK_START_TOLERANCE_S = 3.0
MAX_HOOK_JUMP_S = 30.0
MAX_HOOK_BODY_RATIO = 0.4


def ensure_dirs() -> None:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
