"""Pydantic request/response schemas for the Clipping Engine API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Auth ─────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Job config ───────────────────────────────────────────────────────────────

class WhisperModel(str, Enum):
    tiny = "tiny"
    base = "base"
    small = "small"
    medium = "medium"
    large = "large"


class JobCreateRequest(BaseModel):
    """All configurable pipeline parameters — matches run_pipeline() kwargs."""

    # Core pipeline
    top_k: int = Field(default=2, ge=1, le=10, description="Number of clips to extract")
    clip_duration: float = Field(default=60.0, ge=15.0, le=120.0, description="Target clip length in seconds")
    model_size: WhisperModel = Field(default=WhisperModel.base, description="Whisper model size")
    min_score: int = Field(default=40, ge=0, le=100, description="Minimum virality score threshold")
    llm_model: Optional[str] = Field(default=None, description="OpenRouter model ID override")

    # Post-processing toggles
    enable_hooks: bool = Field(default=True, description="Hook-first reordering")
    enable_captions: bool = Field(default=True, description="Burn-in subtitles")
    enable_enhancements: bool = Field(default=True, description="Visual/audio enhancements")
    vertical: bool = Field(default=False, description="9:16 reframe for Shorts/Reels/TikTok")

    # Advanced enhancement options
    fade_in: float = Field(default=0.3, ge=0.0, le=2.0, description="Fade-in duration in seconds")
    fade_out: float = Field(default=0.5, ge=0.0, le=2.0, description="Fade-out duration in seconds")
    normalize_audio: bool = Field(default=True, description="EBU R128 loudness normalization")
    progress_bar: bool = Field(default=True, description="Animated progress bar overlay")
    caption_font: str = Field(default="Arial", description="Subtitle font face")
    caption_font_size: int = Field(default=22, ge=10, le=72, description="Subtitle font size")


# ── Job response ─────────────────────────────────────────────────────────────

class ClipResult(BaseModel):
    path: str
    start: float
    end: float
    duration: float
    virality_score: Any = None
    confidence: Optional[int] = None
    hook_strength: Optional[int] = None
    standalone_score: Optional[int] = None
    curiosity_score: Optional[int] = None
    reason: str = ""
    reason_short: Optional[str] = None
    hook_text: str = ""
    transcript_text: str = ""


class JobResult(BaseModel):
    total_segments: int = 0
    total_chunks: int = 0
    selected_clips: int = 0
    clips: List[ClipResult] = []


class JobResponse(BaseModel):
    id: str
    status: str
    progress: Optional[str] = None
    error: Optional[str] = None
    config: Dict[str, Any] = {}
    result: Optional[JobResult] = None
    video_filename: str = ""
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
