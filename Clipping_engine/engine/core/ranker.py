"""LLM-powered clip ranker — scores transcript segments for virality.

Uses OpenRouter as the single unified API gateway.  The LLM receives
the FULL transcript (every segment, no compression) and has complete
freedom to pick the best clips.

Models:  Gemini 2.5 Flash (primary) → Qwen3 32B (fallback)

Post-processing enforces NLP-based sentence boundaries, deduplication,
diversity, and minimum quality thresholds.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional, Set

from openai import OpenAI

from engine.config import (
    DIVERSITY_MIN_GAP_S,
    FALLBACK_MODEL,
    MIN_STANDALONE_SCORE,
    OPENROUTER_API_KEY,
    PRIMARY_MODEL,
    TRANSCRIPT_OVERLAP_THRESHOLD,
)

_SYSTEM_PROMPT = """\
You are an expert viral-content editor who has produced thousands of
top-performing short-form clips for YouTube Shorts, TikTok, and Instagram Reels.

You are given the COMPLETE transcript of a video, broken into timestamped
segments.  Read the ENTIRE transcript carefully to understand the full
conversational flow, then select the {top_k} most engaging, standalone clips
of approximately {clip_duration} seconds each.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECTION CRITERIA (ranked by importance):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. HOOK QUALITY — The opening of each clip is CRITICAL.
   The first 3-5 seconds MUST contain a genuine scroll-stopping hook:
   a shocking revelation, a provocative question, a dramatic claim,
   a bold personal statement, or an emotional high-point.

   HARD RULES for hooks:
   - The hook MUST be a strong, self-contained opening statement.
   - NEVER start a clip with filler or transitional words/phrases like:
     "So", "And", "But", "Yeah", "Like", "I mean", "You know",
     "Okay so", "Well", "Right", "Um", "Uh", "Oh", "Basically".
   - NEVER start mid-conversation. The clip must feel like a fresh start.
   - A viewer seeing this clip with ZERO context must instantly understand
     the topic and be pulled in.
   - Good hooks: "I was a crack dealer at 16.", "Nobody tells you this
     about success.", "The biggest lie in business is..."
   - Bad hooks: "So what happened was...", "And then he said...",
     "Yeah, that's the thing about..."

2. STANDALONE VALUE — Each clip MUST make complete sense on its own.
   Imagine a random person scrolling TikTok sees this clip cold.
   They should immediately understand what's being discussed,
   who is speaking about what, and feel compelled to keep watching.
   If it requires prior context from the video, it's NOT standalone.

3. EMOTIONAL INTENSITY — Prefer segments with genuine tension, mystery,
   conflict, surprise, humor, vulnerability, or strong opinions.
   Look for moments where the speaker is passionate, animated, or
   revealing something personal or controversial.

4. CURIOSITY GAP — Prefer segments that open a loop (question, mystery,
   unresolved tension, "but then...") that keeps viewers watching until
   the end.

5. COMPLETE SENTENCES — This is CRITICAL:
   - Every clip MUST start at the beginning of a complete sentence.
   - Every clip MUST end at the end of a complete sentence.
   - NEVER cut mid-sentence, mid-thought, or mid-word.
   - The clip should feel like a natural, complete excerpt — not a
     choppy edit.
   - If a perfect hook starts mid-sentence, move the start to the
     nearest preceding sentence boundary.

6. VARIETY — Spread clips across the full video. Don't pick segments
   that are close together or cover the same topic/anecdote.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIMESTAMP RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Use the exact segment timestamps provided; do NOT invent new ones.
- A clip's "start" must be a segment's "start" value.
- A clip's "end" must be a segment's "end" value.
- You may combine multiple consecutive segments into one clip.
- Aim for ~{clip_duration}s per clip but prioritise natural sentence
  boundaries over exact duration.
- It is better to have a slightly shorter or longer clip that starts
  and ends cleanly than one that hits the exact duration but cuts
  mid-thought.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY a JSON array (no markdown, no explanation) with this schema:
[
  {{
    "rank": 1,
    "start": <float>,
    "end": <float>,
    "hook_text": "<the EXACT text of the first 1-2 sentences that form the hook — must be a strong standalone opening>",
    "virality_score": <int 1-100>,
    "confidence": <int 1-100>,
    "hook_strength": <int 1-100>,
    "standalone_score": <int 1-100>,
    "curiosity_score": <int 1-100>,
    "reason": "<1-sentence explanation of why this clip is compelling>",
    "reason_short": "<1-3 word tag, e.g. bold claim, emotional peak>"
  }}
]
Sort by virality_score descending (best first).

FINAL CHECK before responding:
- Re-read each hook_text. Does it start with a filler word? REJECT it.
- Does each clip make sense to someone who hasn't seen the video? If not, REJECT it.
- Does each clip start AND end on a complete sentence? If not, FIX it.\
"""

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 10

_SENTENCE_ENDERS = frozenset(".!?")

_FILLER_STARTS = re.compile(
    r"^(so|and|but|yeah|like|i mean|you know|okay so|well|right|"
    r"um|uh|oh|basically|anyway|honestly)\b",
    re.IGNORECASE,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _word_set(text: str) -> Set[str]:
    return set(text.lower().split())


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _segments_in_range(
    segments: List[Dict[str, Any]], start: float, end: float,
) -> List[Dict[str, Any]]:
    return [
        s for s in segments
        if float(s["start"]) >= start - 0.05 and float(s["end"]) <= end + 0.05
    ]


def _transcript_for_range(
    segments: List[Dict[str, Any]], start: float, end: float,
) -> str:
    return " ".join(
        s["text"].strip()
        for s in _segments_in_range(segments, start, end)
    ).strip()


def _build_user_prompt(
    segments: List[Dict[str, Any]],
    top_k: int,
    clip_duration: float,
) -> str:
    total_duration = 0.0
    if segments:
        total_duration = float(segments[-1]["end"]) - float(segments[0]["start"])

    lines = [
        f"FULL VIDEO TRANSCRIPT ({len(segments)} segments, "
        f"{total_duration:.0f}s total):",
        "",
    ]
    for seg in segments:
        lines.append(f"[{seg['start']:.2f} - {seg['end']:.2f}] {seg['text']}")

    lines.append("")
    lines.append(
        f"Read the ENTIRE transcript above carefully. "
        f"Understand the full conversational flow, topics discussed, "
        f"and emotional arcs. Then select the {top_k} best clips of "
        f"~{clip_duration}s each.\n\n"
        f"Each clip should be a self-contained, compelling moment that "
        f"would work as a standalone short-form video. "
        f"Make sure every clip starts with a STRONG hook (no filler words) "
        f"and ends on a complete sentence.\n\n"
        f"Return ONLY the JSON array."
    )
    return "\n".join(lines)


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in ("429", "rate_limit", "resource_exhausted", "quota"))


def _nearest_segment_start_index(segments: List[Dict[str, Any]], ts: float) -> int:
    best_i = 0
    best_dist = float("inf")
    for i, seg in enumerate(segments):
        dist = abs(float(seg["start"]) - ts)
        if dist < best_dist:
            best_i = i
            best_dist = dist
    return best_i


def _nearest_segment_end_index(segments: List[Dict[str, Any]], ts: float) -> int:
    best_i = 0
    best_dist = float("inf")
    for i, seg in enumerate(segments):
        dist = abs(float(seg["end"]) - ts)
        if dist < best_dist:
            best_i = i
            best_dist = dist
    return best_i


# ── NLP sentence boundary utilities ─────────────────────────────────────────

def _find_sentence_boundary_index(
    segments: List[Dict[str, Any]],
    near_idx: int,
    direction: str = "forward",
    max_drift: int = 5,
) -> int:
    """Find the nearest segment whose text ends on a sentence boundary."""
    n = len(segments)

    if 0 <= near_idx < n:
        txt = segments[near_idx]["text"].strip()
        if txt and txt[-1] in _SENTENCE_ENDERS:
            return near_idx

    if direction == "forward":
        for offset in range(1, max_drift + 1):
            idx = near_idx + offset
            if idx >= n:
                break
            txt = segments[idx]["text"].strip()
            if txt and txt[-1] in _SENTENCE_ENDERS:
                return idx
    else:
        for offset in range(1, max_drift + 1):
            idx = near_idx - offset
            if idx < 0:
                break
            txt = segments[idx]["text"].strip()
            if txt and txt[-1] in _SENTENCE_ENDERS:
                return idx

    return near_idx


def _find_sentence_start_index(
    segments: List[Dict[str, Any]],
    near_idx: int,
    max_drift: int = 5,
) -> int:
    """Find a segment that begins a new sentence (previous seg ends with .!?)."""
    if near_idx == 0:
        return 0

    for offset in range(0, max_drift + 1):
        idx = near_idx - offset
        if idx <= 0:
            return 0
        prev_text = segments[idx - 1]["text"].strip()
        if prev_text and prev_text[-1] in _SENTENCE_ENDERS:
            return idx

    return near_idx


# ── Duration enforcement ────────────────────────────────────────────────────

def _enforce_clip_durations(
    ranked: List[Dict[str, Any]],
    segments: List[Dict[str, Any]],
    clip_duration: float,
) -> List[Dict[str, Any]]:
    """Expand very short LLM-selected clips to practical durations."""
    if not ranked or not segments:
        return ranked

    min_duration = max(20.0, clip_duration * 0.7)
    max_duration = max(min_duration, clip_duration * 1.3)
    n = len(segments)

    adjusted: List[Dict[str, Any]] = []
    for clip in ranked:
        start = float(clip["start"])
        end = float(clip["end"])
        if end < start:
            start, end = end, start

        start_idx = _nearest_segment_start_index(segments, start)
        end_idx = _nearest_segment_end_index(segments, end)
        if end_idx < start_idx:
            end_idx = start_idx

        while end_idx < n - 1:
            dur = float(segments[end_idx]["end"]) - float(segments[start_idx]["start"])
            if dur >= min_duration:
                break
            end_idx += 1

        while start_idx > 0:
            dur = float(segments[end_idx]["end"]) - float(segments[start_idx]["start"])
            if dur >= min_duration:
                break
            start_idx -= 1

        while end_idx > start_idx:
            dur = float(segments[end_idx]["end"]) - float(segments[start_idx]["start"])
            if dur <= max_duration:
                break
            end_idx -= 1

        out = dict(clip)
        out["start"] = float(segments[start_idx]["start"])
        out["end"] = float(segments[end_idx]["end"])
        adjusted.append(out)

    return adjusted


# ── Sentence-safe boundary snapping (NLP-aware) ─────────────────────────────

def _snap_to_sentence_boundaries(
    ranked: List[Dict[str, Any]],
    segments: List[Dict[str, Any]],
    clip_duration: float,
) -> List[Dict[str, Any]]:
    """Snap both clip start and end to real sentence boundaries."""
    if not ranked or not segments:
        return ranked

    max_allowed = clip_duration * 1.4
    adjusted: List[Dict[str, Any]] = []

    for clip in ranked:
        start = float(clip["start"])
        end = float(clip["end"])

        start_idx = _nearest_segment_start_index(segments, start)
        end_idx = _nearest_segment_end_index(segments, end)

        new_start_idx = _find_sentence_start_index(segments, start_idx, max_drift=5)
        new_end_idx = _find_sentence_boundary_index(
            segments, end_idx, direction="forward", max_drift=5,
        )

        new_start = float(segments[new_start_idx]["start"])
        new_end = float(segments[new_end_idx]["end"])

        if new_end - new_start > max_allowed:
            new_end_idx = _find_sentence_boundary_index(
                segments, end_idx, direction="backward", max_drift=5,
            )
            new_end = float(segments[new_end_idx]["end"])

        if new_end <= new_start:
            new_start = float(segments[start_idx]["start"])
            new_end = float(segments[end_idx]["end"])

        out = dict(clip)
        out["start"] = new_start
        out["end"] = new_end
        adjusted.append(out)

    return adjusted


# ── Deduplication & diversity ───────────────────────────────────────────────

def _deduplicate_clips(
    ranked: List[Dict[str, Any]],
    segments: List[Dict[str, Any]],
    *,
    overlap_threshold: float = TRANSCRIPT_OVERLAP_THRESHOLD,
    min_gap: float = DIVERSITY_MIN_GAP_S,
    min_score: int = MIN_STANDALONE_SCORE,
) -> List[Dict[str, Any]]:
    """Remove overlapping, duplicate, or weak clips."""
    ranked_sorted = sorted(
        ranked,
        key=lambda c: c.get("virality_score", 0),
        reverse=True,
    )

    kept: List[Dict[str, Any]] = []
    kept_word_sets: List[Set[str]] = []

    for clip in ranked_sorted:
        score = clip.get("virality_score", 0)
        if score < min_score:
            print(f"[ranker] Rejected clip (score {score} < {min_score}): "
                  f"{clip.get('reason_short', clip.get('reason', ''))[:60]}")
            continue

        c_start = float(clip["start"])
        c_end = float(clip["end"])
        c_text = _transcript_for_range(segments, c_start, c_end)
        c_words = _word_set(c_text)

        dominated = False
        for i, kept_clip in enumerate(kept):
            k_start = float(kept_clip["start"])
            k_end = float(kept_clip["end"])

            if c_start < k_end and c_end > k_start:
                dominated = True
                break
            if abs(c_start - k_start) < min_gap:
                dominated = True
                break
            if _jaccard(c_words, kept_word_sets[i]) > overlap_threshold:
                dominated = True
                break

        if dominated:
            print(f"[ranker] Deduplicated clip @ {c_start:.1f}s-{c_end:.1f}s")
            continue

        kept.append(clip)
        kept_word_sets.append(c_words)

    return kept


# ── Hook quality validation ──────────────────────────────────────────────────

def _validate_hooks(
    ranked: List[Dict[str, Any]],
    segments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Fix clips whose hook_text starts with filler words."""
    validated: List[Dict[str, Any]] = []
    for clip in ranked:
        out = dict(clip)
        hook = out.get("hook_text", "").strip()

        if hook and _FILLER_STARTS.match(hook):
            c_start = float(out["start"])
            c_end = float(out["end"])
            clip_segs = _segments_in_range(segments, c_start, c_end)

            fixed = False
            for seg in clip_segs:
                seg_text = seg["text"].strip()
                if seg_text and not _FILLER_STARTS.match(seg_text):
                    prev_idx = _nearest_segment_start_index(segments, float(seg["start"]))
                    if prev_idx == 0 or (
                        prev_idx > 0
                        and segments[prev_idx - 1]["text"].strip()[-1:] in _SENTENCE_ENDERS
                    ):
                        out["start"] = float(seg["start"])
                        out["hook_text"] = seg_text
                        fixed = True
                        print(f"[ranker] Fixed filler hook -> new start at {seg['start']:.1f}s")
                        break

            if not fixed:
                print(f"[ranker] Warning: filler hook could not auto-fix: "
                      f"'{hook[:60]}...'")

        validated.append(out)
    return validated


# ── Sentence boundary validation ────────────────────────────────────────────

def _validate_sentence_completeness(
    ranked: List[Dict[str, Any]],
    segments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Verify each clip ends on a sentence boundary."""
    validated: List[Dict[str, Any]] = []
    for clip in ranked:
        out = dict(clip)
        c_start = float(out["start"])
        c_end = float(out["end"])
        transcript = _transcript_for_range(segments, c_start, c_end)

        if transcript and transcript.rstrip()[-1] not in _SENTENCE_ENDERS:
            end_idx = _nearest_segment_end_index(segments, c_end)
            fixed_idx = _find_sentence_boundary_index(
                segments, end_idx, direction="forward", max_drift=3,
            )
            out["end"] = float(segments[fixed_idx]["end"])
            print(f"[ranker] Extended clip end to sentence boundary at "
                  f"{segments[fixed_idx]['end']:.1f}s")

        validated.append(out)
    return validated


# ── Metadata enrichment ─────────────────────────────────────────────────────

_METADATA_FIELDS = (
    "confidence", "hook_strength", "standalone_score",
    "curiosity_score", "reason_short",
)


def _enrich_metadata(
    ranked: List[Dict[str, Any]],
    segments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Attach computed metadata and default missing LLM fields."""
    enriched: List[Dict[str, Any]] = []
    for clip in ranked:
        out = dict(clip)
        for field in _METADATA_FIELDS:
            out.setdefault(field, None)
        out.setdefault("reason", "")
        out.setdefault("hook_text", "")

        c_start = float(out["start"])
        c_end = float(out["end"])
        out["duration"] = round(c_end - c_start, 2)
        out["transcript_text"] = _transcript_for_range(segments, c_start, c_end)
        out.setdefault("heuristic_score", None)

        enriched.append(out)
    return enriched


# ── OpenRouter LLM backend ──────────────────────────────────────────────────

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
) -> List[Dict[str, Any]]:
    """Send a request to a single model via OpenRouter and parse the JSON."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        for val in parsed.values():
            if isinstance(val, list):
                return val
        raise ValueError(f"Model returned dict with no list: {list(parsed.keys())}")
    return parsed


def _call_llm(
    segments: List[Dict[str, Any]],
    top_k: int,
    clip_duration: float,
    model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Call OpenRouter with automatic fallback between models."""
    client = _get_client()
    system = _SYSTEM_PROMPT.format(top_k=top_k, clip_duration=clip_duration)
    user = _build_user_prompt(segments, top_k, clip_duration)

    models = [model] if model else [PRIMARY_MODEL, FALLBACK_MODEL]

    errors: List[str] = []
    for m in models:
        for attempt in range(_MAX_RETRIES):
            try:
                print(f"[ranker] Trying {m}...")
                result = _call_model(client, m, system, user)
                print(f"[ranker] {m} returned {len(result)} clips")
                return result
            except Exception as exc:
                if _is_rate_limit_error(exc) and attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_BASE_DELAY * (attempt + 1)
                    print(f"[ranker] {m} rate-limited, retrying in {delay}s "
                          f"(attempt {attempt + 1}/{_MAX_RETRIES})...")
                    time.sleep(delay)
                else:
                    errors.append(f"{m}: {exc}")
                    print(f"[ranker] {m} failed: {exc}")
                    break

    raise RuntimeError(
        "All models failed:\n" + "\n".join(f"  - {e}" for e in errors)
    )


# ── Public API ──────────────────────────────────────────────────────────────

def rank_clips(
    segments: List[Dict[str, Any]],
    *,
    top_k: int = 3,
    clip_duration: float = 60.0,
    model: Optional[str] = None,
    min_score: int = MIN_STANDALONE_SCORE,
) -> List[Dict[str, Any]]:
    """AI-first ranking: send full transcript to LLM via OpenRouter.

    The LLM sees ALL segments and has full freedom to choose the best
    clips.  Post-processing enforces sentence boundaries, validates
    hook quality, deduplicates, and enriches metadata.

    ``model`` overrides the default model (e.g. "google/gemini-2.5-flash").
    """
    print(f"[ranker] Sending full transcript ({len(segments)} segments) to LLM...")
    print(f"[ranker] Requesting top {top_k} clips of ~{clip_duration}s each")

    raw = _call_llm(segments, top_k, clip_duration, model)
    print(f"[ranker] LLM returned {len(raw)} clips")

    result = _enforce_clip_durations(raw, segments, clip_duration)
    result = _snap_to_sentence_boundaries(result, segments, clip_duration)
    result = _validate_hooks(result, segments)
    result = _validate_sentence_completeness(result, segments)
    result = _deduplicate_clips(result, segments, min_score=min_score)
    result = _enrich_metadata(result, segments)

    print(f"[ranker] Final: {len(result)} clips after post-processing")
    return result
