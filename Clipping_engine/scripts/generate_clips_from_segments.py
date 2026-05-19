"""Generate ranked clips from existing transcript segments.

This script skips audio extraction + Whisper transcription and reuses
`outputs/segments.json` to:
  1) rank clips via OpenRouter (Gemini 2.5 Flash / Qwen3 fallback)
  2) run hook/caption/enhancement stages
  3) save final clips to outputs/clip_{i}.mp4
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import engine.config as cfg
from engine.config import MIN_STANDALONE_SCORE
from engine.core.captions import burn_captions, generate_ass_subtitles
from engine.core.enhance import enhance_clip
from engine.core.hooks import find_hook_timestamps, reorder_with_hook
from engine.core.ranker import rank_clips


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate clips from existing segments.json")
    parser.add_argument(
        "--video",
        default="Jim Rohn Motivation.mp4",
        help="Input video file path (default: Jim Rohn Motivation.mp4)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of clips to request from ranker",
    )
    parser.add_argument(
        "--clip-duration",
        type=float,
        default=60.0,
        help="Target duration hint for ranker",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="OpenRouter model ID (default: auto-fallback chain). "
             "Examples: google/gemini-2.5-flash, qwen/qwen3-32b",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=MIN_STANDALONE_SCORE,
        help="Minimum virality score to keep a clip",
    )
    parser.add_argument(
        "--vertical",
        action="store_true",
        help="Enable 9:16 reframe in enhancement stage",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg.ensure_dirs()

    input_video = ROOT_DIR / args.video
    segments_path = cfg.OUTPUTS_DIR / "segments.json"
    if not input_video.exists():
        raise FileNotFoundError(f"Missing input video: {input_video}")
    if not segments_path.exists():
        raise FileNotFoundError(f"Missing segments file: {segments_path}")

    segments = json.loads(segments_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(segments)} segments from {segments_path}")

    ranked = rank_clips(
        segments,
        top_k=args.top_k,
        clip_duration=args.clip_duration,
        model=args.model,
        min_score=args.min_score,
    )
    ranked_path = cfg.OUTPUTS_DIR / "ranked_clips.json"
    ranked_path.write_text(json.dumps(ranked, indent=2), encoding="utf-8")
    print(f"Ranked clips saved to: {ranked_path} (count={len(ranked)})")

    for i, clip_info in enumerate(ranked, start=1):
        clip_start = float(clip_info["start"])
        clip_end = float(clip_info["end"])
        score = clip_info.get("virality_score", "?")
        print(f"\n--- Clip {i}/{len(ranked)} "
              f"({clip_start:.1f}s - {clip_end:.1f}s, score={score}) ---")

        raw_path = cfg.TEMP_DIR / f"raw_clip_{i}.mp4"
        final_path = cfg.OUTPUTS_DIR / f"clip_{i}.mp4"

        hook_start, hook_end = find_hook_timestamps(clip_info, segments)
        reorder_with_hook(
            str(input_video),
            clip_start,
            clip_end,
            hook_start,
            hook_end,
            str(raw_path),
        )

        sub_path = cfg.TEMP_DIR / f"clip_{i}.ass"
        generate_ass_subtitles(
            segments,
            str(sub_path),
            clip_start=clip_start,
            clip_end=clip_end,
        )
        captioned_path = cfg.TEMP_DIR / f"captioned_clip_{i}.mp4"
        burn_captions(str(raw_path), str(sub_path), str(captioned_path))

        enhanced_path = cfg.TEMP_DIR / f"enhanced_clip_{i}.mp4"
        enhance_clip(
            str(captioned_path),
            str(enhanced_path),
            vertical=args.vertical,
            fade=True,
            normalize=True,
            progress_bar=True,
        )

        shutil.copy2(str(enhanced_path), str(final_path))
        print(f"Saved: {final_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
