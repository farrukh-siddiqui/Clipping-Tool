"""Full clipping-engine pipeline — from raw video to viral-ready shorts.

Stages:
  1. Audio extraction (FFmpeg)
  2. Transcription (Whisper)
  3. Chunking (time-based sentence grouping)
  4. AI-first ranking (full transcript → LLM with sentence/hook validation)
  5. Hook-first clip assembly
  6. Auto-captions (ASS burn-in)
  7. Visual & audio enhancements (reframe, fade, normalize, progress bar)
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import engine.config as cfg
from engine.config import MIN_STANDALONE_SCORE
from engine.core.captions import burn_captions, generate_ass_subtitles
from engine.core.chunker import create_chunks
from engine.core.cutter import cut_clip
from engine.core.enhance import enhance_clip
from engine.core.ffmpeg import extract_audio
from engine.core.hooks import find_hook_timestamps, reorder_with_hook
from engine.core.ranker import rank_clips
from engine.core.transcribe import transcribe


def run_pipeline(
    video_path: str,
    *,
    model_size: str = "base",
    chunk_duration: float = 60.0,
    top_k: int = 2,
    clip_duration: float = 60.0,
    llm_model: Optional[str] = None,
    min_score: int = MIN_STANDALONE_SCORE,
    enable_hooks: bool = True,
    enable_captions: bool = True,
    enable_enhancements: bool = True,
    vertical: bool = False,
    on_progress: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Run the full intelligent clipping pipeline.

    Parameters
    ----------
    video_path : str
        Path to the source video file.
    model_size : str
        Whisper model size (tiny/base/small/medium/large).
    chunk_duration : float
        Max duration (seconds) for the initial chunker pass.
    top_k : int
        Number of clips to extract.
    clip_duration : float
        Target clip length hint passed to the LLM ranker.
    llm_model : str or None
        OpenRouter model ID, or None for auto-fallback.
    min_score : int
        Minimum virality_score to keep a clip (rejects weaker ones).
    enable_hooks : bool
        Whether to reorder clips so the hook plays first.
    enable_captions : bool
        Whether to burn auto-generated subtitles.
    enable_enhancements : bool
        Whether to apply visual/audio enhancements.
    vertical : bool
        Whether to reframe to 9:16 (for Shorts/Reels/TikTok).
    on_progress : callable or None
        Optional callback invoked with human-readable status (e.g. ``Stage 2/7: ...``).
    """
    def _p(msg: str) -> None:
        if on_progress is not None:
            on_progress(msg)

    cfg.ensure_dirs()

    input_video = Path(video_path)
    if not input_video.exists():
        raise FileNotFoundError(f"Input video not found: {video_path}")

    audio_path = cfg.TEMP_DIR / "audio.wav"
    segments_path = cfg.OUTPUTS_DIR / "segments.json"
    chunks_path = cfg.OUTPUTS_DIR / "chunks.json"
    ranked_path = cfg.OUTPUTS_DIR / "ranked_clips.json"

    # ── Stage 1: Audio extraction ───────────────────────────────────────
    print("[pipeline] Stage 1/7: Extracting audio...")
    _p("Stage 1/7: Extracting audio...")
    extract_audio(str(input_video), str(audio_path))

    # ── Stage 2: Transcription ──────────────────────────────────────────
    print("[pipeline] Stage 2/7: Transcribing with Whisper...")
    _p("Stage 2/7: Transcribing with Whisper...")
    segments = transcribe(str(audio_path), model_size=model_size)
    segments_path.write_text(json.dumps(segments, indent=2), encoding="utf-8")

    # ── Stage 3: Chunking ───────────────────────────────────────────────
    print("[pipeline] Stage 3/7: Creating chunks...")
    _p("Stage 3/7: Creating chunks...")
    chunks = create_chunks(segments, max_duration=chunk_duration)
    chunks_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")

    # ── Stage 4: AI-first ranking ────────────────────────────────────────
    print("[pipeline] Stage 4/7: Ranking clips (full transcript → LLM)...")
    _p("Stage 4/7: Ranking clips (AI)...")
    ranked = rank_clips(
        segments,
        top_k=top_k,
        clip_duration=clip_duration,
        model=llm_model,
        min_score=min_score,
    )
    ranked_path.write_text(json.dumps(ranked, indent=2), encoding="utf-8")

    # ── Stage 5-7: Clip assembly ────────────────────────────────────────
    clip_results: List[Dict[str, Any]] = []

    n_clips = len(ranked)
    for i, clip_info in enumerate(ranked, start=1):
        clip_start = float(clip_info["start"])
        clip_end = float(clip_info["end"])
        score = clip_info.get("virality_score", "?")
        print(f"\n[pipeline] Clip {i}/{len(ranked)} "
              f"({clip_start:.1f}s - {clip_end:.1f}s, score={score})")

        raw_clip_path = cfg.TEMP_DIR / f"raw_clip_{i}.mp4"
        final_clip_path = cfg.OUTPUTS_DIR / f"clip_{i}.mp4"

        # Stage 5: Hook reordering
        _p(f"Stage 5/7: Clip {i}/{n_clips} — Cutting & hooks...")
        if enable_hooks:
            print(f"  [Stage 5] Extracting hook...")
            hook_start, hook_end = find_hook_timestamps(clip_info, segments)
            reorder_with_hook(
                str(input_video),
                clip_start, clip_end,
                hook_start, hook_end,
                str(raw_clip_path),
            )
        else:
            cut_clip(str(input_video), clip_start, clip_end, str(raw_clip_path))

        current_path = raw_clip_path

        # Stage 6: Auto-captions
        if enable_captions:
            _p(f"Stage 6/7: Clip {i}/{n_clips} — Burning captions...")
            print(f"  [Stage 6] Generating captions...")
            sub_path = cfg.TEMP_DIR / f"clip_{i}.ass"
            generate_ass_subtitles(
                segments,
                str(sub_path),
                clip_start=clip_start,
                clip_end=clip_end,
            )
            captioned_path = cfg.TEMP_DIR / f"captioned_clip_{i}.mp4"
            burn_captions(str(current_path), str(sub_path), str(captioned_path))
            current_path = captioned_path
        else:
            _p(f"Stage 6/7: Clip {i}/{n_clips} — Captions skipped")

        # Stage 7: Enhancements
        if enable_enhancements:
            _p(f"Stage 7/7: Clip {i}/{n_clips} — Final polish...")
            print(f"  [Stage 7] Applying enhancements...")
            enhanced_path = cfg.TEMP_DIR / f"enhanced_clip_{i}.mp4"
            enhance_clip(
                str(current_path),
                str(enhanced_path),
                vertical=vertical,
                fade=True,
                normalize=True,
                progress_bar=True,
            )
            current_path = enhanced_path
        else:
            _p(f"Stage 7/7: Clip {i}/{n_clips} — Enhancements skipped")

        shutil.copy2(str(current_path), str(final_clip_path))

        clip_results.append({
            "path": str(final_clip_path),
            "start": clip_start,
            "end": clip_end,
            "duration": clip_info.get("duration", clip_end - clip_start),
            "virality_score": score,
            "confidence": clip_info.get("confidence"),
            "hook_strength": clip_info.get("hook_strength"),
            "standalone_score": clip_info.get("standalone_score"),
            "curiosity_score": clip_info.get("curiosity_score"),
            "heuristic_score": clip_info.get("heuristic_score"),
            "reason": clip_info.get("reason", ""),
            "reason_short": clip_info.get("reason_short"),
            "hook_text": clip_info.get("hook_text", ""),
            "transcript_text": clip_info.get("transcript_text", ""),
        })

    print(f"\n[pipeline] Done! Generated {len(clip_results)} clips.")

    return {
        "audio_path": str(audio_path),
        "segments_path": str(segments_path),
        "chunks_path": str(chunks_path),
        "ranked_path": str(ranked_path),
        "clips": clip_results,
        "total_segments": len(segments),
        "total_chunks": len(chunks),
        "selected_clips": len(clip_results),
    }


def run_pipeline_basic(
    video_path: str,
    *,
    model_size: str = "base",
    chunk_duration: float = 60.0,
    top_k: int = 2,
) -> Dict[str, Any]:
    """Original basic pipeline — no LLM, no hooks, no enhancements.

    Kept for backward compatibility and quick testing without API keys.
    """
    cfg.ensure_dirs()

    input_video = Path(video_path)
    if not input_video.exists():
        raise FileNotFoundError(f"Input video not found: {video_path}")

    audio_path = cfg.TEMP_DIR / "audio.wav"
    segments_path = cfg.OUTPUTS_DIR / "segments.json"
    chunks_path = cfg.OUTPUTS_DIR / "chunks.json"

    extract_audio(str(input_video), str(audio_path))
    segments = transcribe(str(audio_path), model_size=model_size)
    chunks = create_chunks(segments, max_duration=chunk_duration)

    segments_path.write_text(json.dumps(segments, indent=2), encoding="utf-8")
    chunks_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")

    selected = chunks[:top_k]
    clip_paths: List[str] = []
    for i, chunk in enumerate(selected, start=1):
        clip_path = cfg.OUTPUTS_DIR / f"clip_{i}.mp4"
        cut_clip(
            str(input_video),
            float(chunk["start"]),
            float(chunk["end"]),
            str(clip_path),
        )
        clip_paths.append(str(clip_path))

    return {
        "audio_path": str(audio_path),
        "segments_path": str(segments_path),
        "chunks_path": str(chunks_path),
        "clips": clip_paths,
        "total_segments": len(segments),
        "total_chunks": len(chunks),
        "selected_chunks": len(selected),
    }
