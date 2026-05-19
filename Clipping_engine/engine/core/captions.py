"""Auto-caption generation — CapCut / Hormozi-style animated subtitles.

Generates styled ASS subtitle files from Whisper segments and burns them
into clips via FFmpeg.  Uses punctuation-aware chunking with minimum
duration and max-CPS constraints so captions feel natural to read.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import pysubs2

from engine.config import (
    CAPTION_FONT,
    CAPTION_FONT_SIZE,
    CAPTION_OUTLINE_WIDTH,
)
from engine.core.ffmpeg import run_ffmpeg

MIN_CAPTION_DURATION = 0.9
MAX_CPS = 14.0
MAX_WORDS_PER_CHUNK = 7


def _seconds_to_ms(seconds: float) -> int:
    return int(round(seconds * 1000))


def _split_into_phrases(text: str) -> List[str]:
    """Split text on punctuation boundaries into readable phrases."""
    raw_parts = re.split(r'(?<=[,.\?!;:])\s+', text)

    phrases: List[str] = []
    for part in raw_parts:
        words = part.split()
        while len(words) > MAX_WORDS_PER_CHUNK:
            phrases.append(" ".join(words[:MAX_WORDS_PER_CHUNK]))
            words = words[MAX_WORDS_PER_CHUNK:]
        if words:
            phrases.append(" ".join(words))

    return phrases if phrases else [text]


def _assign_durations(
    phrases: List[str],
    total_duration: float,
) -> List[float]:
    """Distribute time across phrases proportional to char count, respecting
    MIN_CAPTION_DURATION and MAX_CPS constraints."""
    char_counts = [max(len(p), 1) for p in phrases]
    total_chars = sum(char_counts)

    raw = [(c / total_chars) * total_duration for c in char_counts]

    for i in range(len(raw)):
        if raw[i] < MIN_CAPTION_DURATION:
            raw[i] = MIN_CAPTION_DURATION

    for i in range(len(raw)):
        needed = char_counts[i] / MAX_CPS
        if raw[i] < needed:
            raw[i] = needed

    scale = total_duration / sum(raw) if sum(raw) > 0 else 1.0
    adjusted = [d * scale for d in raw]

    for i in range(len(adjusted)):
        if adjusted[i] < MIN_CAPTION_DURATION:
            adjusted[i] = MIN_CAPTION_DURATION

    return adjusted


def generate_ass_subtitles(
    segments: List[Dict[str, Any]],
    output_path: str,
    clip_start: float = 0.0,
    clip_end: float | None = None,
    style_name: str = "Viral",
) -> str:
    """Create a styled ASS subtitle file from Whisper segments.

    Timestamps are adjusted relative to ``clip_start`` so they align
    with a clip that was cut starting at that position.
    """
    subs = pysubs2.SSAFile()

    style = pysubs2.SSAStyle(
        fontname=CAPTION_FONT,
        fontsize=CAPTION_FONT_SIZE,
        primarycolor=pysubs2.Color(255, 255, 255, 0),
        outlinecolor=pysubs2.Color(0, 0, 0, 0),
        backcolor=pysubs2.Color(0, 0, 0, 128),
        outline=CAPTION_OUTLINE_WIDTH,
        shadow=2,
        alignment=2,  # bottom-center
        marginv=40,
        bold=True,
    )
    subs.styles[style_name] = style

    for seg in segments:
        seg_start = float(seg["start"])
        seg_end = float(seg["end"])

        if seg_end <= clip_start:
            continue
        if clip_end is not None and seg_start >= clip_end:
            break

        relative_start = max(seg_start - clip_start, 0.0)
        relative_end = seg_end - clip_start
        if clip_end is not None:
            relative_end = min(relative_end, clip_end - clip_start)

        text = str(seg["text"]).strip()
        if not text:
            continue

        seg_duration = relative_end - relative_start
        phrases = _split_into_phrases(text)

        if len(phrases) == 1 or seg_duration < MIN_CAPTION_DURATION * 1.5:
            event = pysubs2.SSAEvent(
                start=_seconds_to_ms(relative_start),
                end=_seconds_to_ms(max(relative_end, relative_start + MIN_CAPTION_DURATION)),
                text=text.upper(),
                style=style_name,
            )
            subs.events.append(event)
        else:
            durations = _assign_durations(phrases, seg_duration)
            cursor = relative_start
            for phrase, dur in zip(phrases, durations):
                event = pysubs2.SSAEvent(
                    start=_seconds_to_ms(cursor),
                    end=_seconds_to_ms(cursor + dur),
                    text=phrase.upper(),
                    style=style_name,
                )
                subs.events.append(event)
                cursor += dur

    subs.save(output_path, encoding="utf-8")
    return output_path


def burn_captions(
    input_video: str,
    subtitle_path: str,
    output_path: str,
) -> None:
    """Burn ASS subtitles into a video using FFmpeg."""
    sub_path_escaped = str(Path(subtitle_path).as_posix()).replace(":", "\\:")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", f"ass='{sub_path_escaped}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ])
