"""Hook extraction and reordering.

Implements the "hook-first" technique used by OpusClip / CapCut:
if the most compelling sentence in a clip isn't at the very start,
re-cut the clip so the hook plays first, then the body follows
(starting *after* the hook to avoid duplication).

Guardrails prevent awkward results:
  - Skip reorder when the hook is already near the start.
  - Skip when the hook is too far into the clip (max jump).
  - Skip when the hook would dominate the clip (body ratio).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.config import (
    HOOK_START_TOLERANCE_S,
    MAX_HOOK_BODY_RATIO,
    MAX_HOOK_JUMP_S,
    TAIL_PAD_MS,
)
from engine.core.ffmpeg import run_ffmpeg


def extract_hook_segment(
    input_video: str,
    hook_start: float,
    hook_end: float,
    output_path: str,
) -> None:
    """Cut just the hook portion from the source video (re-encoded for concat safety)."""
    run_ffmpeg([
        "ffmpeg", "-y",
        "-ss", str(hook_start),
        "-to", str(hook_end),
        "-i", input_video,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ])


def extract_body_segment(
    input_video: str,
    body_start: float,
    body_end: float,
    output_path: str,
) -> None:
    """Cut the body (non-hook) portion from the source video."""
    run_ffmpeg([
        "ffmpeg", "-y",
        "-ss", str(body_start),
        "-to", str(body_end),
        "-i", input_video,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ])


def concat_segments(segment_paths: List[str], output_path: str) -> None:
    """Concatenate multiple video segments using FFmpeg concat demuxer.

    Paths in the concat list must be **absolute** (and stable for FFmpeg):
    relative paths are resolved by FFmpeg relative to the list file's
    directory, which duplicates segments like ``jobs/<id>/temp/...`` and
    breaks with "No such file or directory".
    """
    list_file = Path(output_path).resolve().parent / "_concat_list.txt"
    try:
        resolved = [Path(p).resolve() for p in segment_paths]
        # Forward slashes work on Windows FFmpeg and avoid concat demuxer quirks.
        lines = [f"file '{p.as_posix()}'" for p in resolved]
        list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        run_ffmpeg([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            output_path,
        ])
    finally:
        list_file.unlink(missing_ok=True)


def reorder_with_hook(
    input_video: str,
    clip_start: float,
    clip_end: float,
    hook_start: float,
    hook_end: float,
    output_path: str,
    *,
    hook_start_tolerance: float = HOOK_START_TOLERANCE_S,
    max_hook_jump: float = MAX_HOOK_JUMP_S,
    max_hook_body_ratio: float = MAX_HOOK_BODY_RATIO,
    tail_pad: float = TAIL_PAD_MS / 1000.0,
) -> None:
    """Build a clip that leads with the hook, then plays the body.

    The body starts at ``hook_end`` (not ``clip_start``) so the hook
    text is not repeated.

    Reordering is skipped (straight cut instead) when any of these
    guardrails trigger:
      - Hook is already near clip start (within ``hook_start_tolerance``).
      - Hook is too far into the clip (``hook_start - clip_start > max_hook_jump``).
      - Hook duration exceeds ``max_hook_body_ratio`` of total clip length.
    """
    padded_end = clip_end + tail_pad
    clip_dur = clip_end - clip_start
    hook_dur = hook_end - hook_start
    hook_offset = hook_start - clip_start

    skip_reorder = (
        abs(hook_offset) < hook_start_tolerance
        or hook_offset > max_hook_jump
        or (clip_dur > 0 and hook_dur / clip_dur > max_hook_body_ratio)
    )

    if skip_reorder:
        run_ffmpeg([
            "ffmpeg", "-y",
            "-ss", str(clip_start),
            "-to", str(padded_end),
            "-i", input_video,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            output_path,
        ])
        return

    tmp_dir = Path(output_path).parent / "_hook_tmp"
    tmp_dir.mkdir(exist_ok=True)
    hook_path = str(tmp_dir / "hook.mp4")
    body_path = str(tmp_dir / "body.mp4")

    try:
        extract_hook_segment(input_video, hook_start, hook_end, hook_path)
        extract_body_segment(input_video, hook_end, padded_end, body_path)
        concat_segments([hook_path, body_path], output_path)
    finally:
        for f in [hook_path, body_path]:
            Path(f).unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except OSError:
            pass


def find_hook_timestamps(
    ranked_clip: Dict[str, Any],
    segments: List[Dict[str, Any]],
    max_hook_duration: float = 8.0,
) -> tuple[float, float]:
    """Find the hook boundaries from the ranked clip's hook_text.

    Matches ``hook_text`` from the LLM output against the original Whisper
    segments to recover precise timestamps.  Falls back to the first
    ``max_hook_duration`` seconds of the clip if no match is found.
    """
    hook_text = ranked_clip.get("hook_text", "").lower().strip()
    clip_start = float(ranked_clip["start"])
    clip_end = float(ranked_clip["end"])

    if not hook_text:
        return clip_start, min(clip_start + max_hook_duration, clip_end)

    best_start: Optional[float] = None
    best_end: Optional[float] = None

    for seg in segments:
        seg_start = float(seg["start"])
        seg_end = float(seg["end"])
        if seg_start < clip_start - 0.5 or seg_end > clip_end + 0.5:
            continue
        seg_text = seg["text"].lower().strip()
        if seg_text in hook_text or hook_text in seg_text:
            if best_start is None or seg_start < best_start:
                best_start = seg_start
            best_end = seg_end

    if best_start is not None and best_end is not None:
        if best_end - best_start > max_hook_duration:
            best_end = best_start + max_hook_duration
        return best_start, best_end

    return clip_start, min(clip_start + max_hook_duration, clip_end)
