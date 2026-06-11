"""AI-generated social media metadata for clips via OpenRouter.

Given a clip's transcript, hook text, and context, generates SEO-optimized
title, description, and hashtags for YouTube Shorts / TikTok / Reels.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from engine.config import OPENROUTER_API_KEY, PRIMARY_MODEL, FALLBACK_MODEL

_SYSTEM_PROMPT = """\
You are an expert social-media content strategist who writes viral YouTube Shorts metadata.

Given a clip transcript and context, produce a JSON object with exactly these fields:

{{
  "title": "<catchy, SEO-optimized title, max 100 chars, no quotes wrapping it>",
  "description": "<2-3 sentence YouTube Shorts description, include a CTA, max 500 chars>",
  "tags": ["<tag1>", "<tag2>", ...],
  "hashtags": ["#hashtag1", "#hashtag2", ...]
}}

RULES:
- Title: attention-grabbing, clickable, uses power words, includes 1-2 keywords naturally. NO clickbait lies.
- Description: summarize the clip's core message, add a call-to-action (like, subscribe, comment), include 2-3 relevant keywords.
- Tags: 8-15 relevant YouTube tags (no # prefix), mix of broad and niche.
- Hashtags: 5-8 hashtags WITH # prefix, trending and relevant, include #Shorts.
- ALL output must be in English.
- Return ONLY the JSON object, no markdown, no explanation.
"""

_USER_TEMPLATE = """\
CLIP TRANSCRIPT:
{transcript}

HOOK TEXT:
{hook_text}

CLIP CONTEXT:
- Source video: {video_filename}
- Duration: {duration:.0f}s
- Virality score: {virality_score}/100
- Topic hint: {reason}

Generate the title, description, tags, and hashtags for this clip as a YouTube Short.
Return ONLY the JSON object.
"""

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 5


def _get_client() -> OpenAI:
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set. Add it to your .env file.\n"
            "Get a key at https://openrouter.ai/keys"
        )
    return OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )


def _call_model(
    client: OpenAI,
    model: str,
    system: str,
    user: str,
) -> Dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected dict, got {type(parsed).__name__}")

    required = {"title", "description", "tags", "hashtags"}
    missing = required - set(parsed.keys())
    if missing:
        raise ValueError(f"Missing fields: {missing}")

    return parsed


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in ("429", "rate_limit", "resource_exhausted", "quota"))


def generate_clip_metadata(
    transcript_text: str,
    hook_text: str = "",
    video_filename: str = "video",
    duration: float = 60.0,
    virality_score: int = 0,
    reason: str = "",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate title, description, tags, and hashtags for a clip."""
    client = _get_client()

    user_prompt = _USER_TEMPLATE.format(
        transcript=transcript_text[:4000],
        hook_text=hook_text[:500],
        video_filename=video_filename,
        duration=duration,
        virality_score=virality_score,
        reason=reason,
    )

    models = [model] if model else [PRIMARY_MODEL, FALLBACK_MODEL]
    errors: List[str] = []

    for m in models:
        for attempt in range(_MAX_RETRIES):
            try:
                print(f"[metadata] Trying {m}...")
                result = _call_model(client, m, _SYSTEM_PROMPT, user_prompt)
                print(f"[metadata] Generated: {result.get('title', '')[:60]}...")

                result["title"] = str(result["title"])[:100]
                result["description"] = str(result["description"])[:500]
                result["tags"] = [str(t) for t in result.get("tags", [])][:15]
                result["hashtags"] = [
                    h if h.startswith("#") else f"#{h}"
                    for h in (str(h) for h in result.get("hashtags", []))
                ][:8]

                if "#Shorts" not in result["hashtags"] and "#shorts" not in result["hashtags"]:
                    result["hashtags"].insert(0, "#Shorts")

                return result
            except Exception as exc:
                if _is_rate_limit_error(exc) and attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_BASE_DELAY * (attempt + 1)
                    print(f"[metadata] Rate-limited, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    errors.append(f"{m}: {exc}")
                    print(f"[metadata] {m} failed: {exc}")
                    break

    raise RuntimeError(
        "Metadata generation failed:\n" + "\n".join(f"  - {e}" for e in errors)
    )
