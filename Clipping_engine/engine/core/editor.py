"""Post-pipeline clip editor — video filters and background music via FFmpeg.

Usage:
    apply_edits(input_path, output_path, filter_id="warm", music_path="bgm.mp3")

Filter presets are pure FFmpeg filter chains (no external LUT files).
Background music is mixed under speech using amix with configurable volume.
"""

from __future__ import annotations

import subprocess
import json as _json
from pathlib import Path
from typing import Optional

from engine.core.ffmpeg import run_ffmpeg

FILTER_PRESETS: dict[str, dict] = {
    "warm": {
        "name": "Warm",
        "description": "Golden warm tones, slightly boosted saturation",
        "ffmpeg_chain": "colorbalance=rs=.15:gs=-.05:bs=-.15,eq=saturation=1.15",
    },
    "cool": {
        "name": "Cool",
        "description": "Blue-shifted cool tones",
        "ffmpeg_chain": "colorbalance=rs=-.1:gs=.05:bs=.2,eq=saturation=1.1",
    },
    "vintage": {
        "name": "Vintage",
        "description": "Faded retro film look",
        "ffmpeg_chain": "curves=vintage,eq=saturation=0.8:brightness=0.03",
    },
    "cinematic": {
        "name": "Cinematic",
        "description": "High contrast, desaturated film grade",
        "ffmpeg_chain": "eq=contrast=1.2:brightness=-0.05:saturation=0.85,unsharp=3:3:0.5",
    },
    "bw": {
        "name": "Black & White",
        "description": "Classic monochrome with boosted contrast",
        "ffmpeg_chain": "hue=s=0,eq=contrast=1.1",
    },
    "high_contrast": {
        "name": "High Contrast",
        "description": "Punchy contrast with vivid colors",
        "ffmpeg_chain": "eq=contrast=1.4:saturation=1.2",
    },
    "muted": {
        "name": "Muted",
        "description": "Soft desaturated pastel look",
        "ffmpeg_chain": "eq=saturation=0.5:brightness=0.05",
    },
    "vivid": {
        "name": "Vivid",
        "description": "Hyper-saturated bold colors",
        "ffmpeg_chain": "eq=saturation=1.5:contrast=1.1",
    },
    "film_grain": {
        "name": "Film Grain",
        "description": "Analog noise with slight desaturation",
        "ffmpeg_chain": "noise=alls=15:allf=t,eq=saturation=0.9",
    },
    "golden_hour": {
        "name": "Golden Hour",
        "description": "Warm sunset glow with soft highlights",
        "ffmpeg_chain": "colorbalance=rs=.2:gs=.1:bs=-.15,eq=brightness=0.05:saturation=1.2",
    },
}


def _probe_duration(path: str) -> float:
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", path],
        capture_output=True, text=True,
    )
    info = _json.loads(probe.stdout)
    return float(info["format"]["duration"])


def apply_filter(input_path: str, output_path: str, filter_id: str) -> None:
    """Apply a named color-grading filter preset to a clip."""
    preset = FILTER_PRESETS.get(filter_id)
    if not preset:
        raise ValueError(f"Unknown filter preset: {filter_id}")

    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", preset["ffmpeg_chain"],
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        output_path,
    ])


def apply_bgm(
    input_path: str,
    output_path: str,
    music_path: str,
    volume: float = 0.12,
    clip_duration: Optional[float] = None,
) -> None:
    """Mix a background music track under the clip's original audio."""
    dur = clip_duration or _probe_duration(input_path)

    filter_complex = (
        f"[1:a]volume={volume},atrim=0:{dur:.3f},apad[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first[out]"
    )
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", input_path,
        "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[out]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ])


def apply_edits(
    input_path: str,
    output_path: str,
    *,
    filter_id: Optional[str] = None,
    music_path: Optional[str] = None,
    music_volume: float = 0.12,
) -> str:
    """Apply filter and/or background music to a clip.

    When both are requested, filter runs first (re-encodes video),
    then BGM is mixed into that result (audio-only, video is copied).
    Returns the final output path.
    """
    if not filter_id and not music_path:
        raise ValueError("At least one of filter_id or music_path is required")

    tmp_dir = Path(output_path).parent / "_edit_tmp"
    tmp_dir.mkdir(exist_ok=True)
    tmp_file = str(tmp_dir / "filtered.mp4")

    try:
        if filter_id and music_path:
            apply_filter(input_path, tmp_file, filter_id)
            apply_bgm(tmp_file, output_path, music_path, volume=music_volume)
        elif filter_id:
            apply_filter(input_path, output_path, filter_id)
        else:
            apply_bgm(input_path, output_path, music_path, volume=music_volume)  # type: ignore[arg-type]

        return output_path
    finally:
        Path(tmp_file).unlink(missing_ok=True)
        if tmp_dir.exists():
            try:
                tmp_dir.rmdir()
            except OSError:
                pass
