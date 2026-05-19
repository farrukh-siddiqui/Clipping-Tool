"""Visual and audio enhancements for clips — all pure FFmpeg, no extra deps.

Provides building-block functions that can be composed in the pipeline:
  - Vertical reframe (16:9 → 9:16) with blurred background
  - Fade in / fade out
  - Audio loudness normalization
  - Animated progress bar overlay
  - Full enhancement chain that applies everything in one FFmpeg pass
"""

from __future__ import annotations

from typing import List, Optional

from engine.core.ffmpeg import run_ffmpeg


def reframe_vertical(
    input_path: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    blur_radius: int = 20,
) -> None:
    """Convert landscape video to 9:16 with blurred-background fill.

    Creates a blurred, scaled copy of the video as background and overlays
    the original (scaled to fit width) centered vertically.
    """
    vf = (
        f"split[bg][fg];"
        f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},boxblur={blur_radius}[bg];"
        f"[fg]scale={width}:-2:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
    )
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ])


def add_fade(
    input_path: str,
    output_path: str,
    fade_in: float = 0.5,
    fade_out: float = 0.5,
    duration: Optional[float] = None,
) -> None:
    """Add fade-in and fade-out transitions."""
    probe_dur = duration
    if probe_dur is None:
        import subprocess, json as _json
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", input_path],
            capture_output=True, text=True,
        )
        info = _json.loads(probe.stdout)
        probe_dur = float(info["format"]["duration"])

    fade_out_start = max(probe_dur - fade_out, 0)
    vf = (
        f"fade=t=in:st=0:d={fade_in},"
        f"fade=t=out:st={fade_out_start:.3f}:d={fade_out}"
    )
    af = (
        f"afade=t=in:st=0:d={fade_in},"
        f"afade=t=out:st={fade_out_start:.3f}:d={fade_out}"
    )
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf,
        "-af", af,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ])


def normalize_audio(input_path: str, output_path: str) -> None:
    """Two-pass EBU R128 loudness normalization."""
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ])


def add_progress_bar(
    input_path: str,
    output_path: str,
    bar_height: int = 6,
    bar_color: str = "0xFFFFFF@0.85",
    duration: Optional[float] = None,
) -> None:
    """Draw an animated progress bar at the bottom of the video."""
    probe_dur = duration
    if probe_dur is None:
        import subprocess, json as _json
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", input_path],
            capture_output=True, text=True,
        )
        info = _json.loads(probe.stdout)
        probe_dur = float(info["format"]["duration"])

    vf = (
        f"drawbox=x=0:y=ih-{bar_height}:"
        f"w='iw*t/{probe_dur:.3f}':"
        f"h={bar_height}:"
        f"color={bar_color}:"
        f"t=fill"
    )
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        output_path,
    ])


def enhance_clip(
    input_path: str,
    output_path: str,
    *,
    vertical: bool = False,
    fade: bool = True,
    fade_in_duration: float = 0.3,
    fade_out_duration: float = 0.5,
    normalize: bool = True,
    progress_bar: bool = True,
    bar_height: int = 6,    
) -> str:
    """Apply all requested enhancements in sequence.

    Each enhancement writes to a temp file that feeds the next step,
    so we avoid stacking complex FFmpeg filter graphs into one command
    (more reliable across FFmpeg versions).

    Returns the final output path.
    """
    from pathlib import Path
    current = input_path
    tmp_dir = Path(output_path).parent / "_enhance_tmp"
    tmp_dir.mkdir(exist_ok=True)
    step = 0
    temps: List[str] = []

    def _next_tmp() -> str:
        nonlocal step
        step += 1
        p = str(tmp_dir / f"step_{step}.mp4")
        temps.append(p)
        return p

    try:
        if vertical:
            out = _next_tmp()
            reframe_vertical(current, out)
            current = out

        if normalize:
            out = _next_tmp()
            normalize_audio(current, out)
            current = out

        if fade:
            out = _next_tmp()
            add_fade(current, out, fade_in=fade_in_duration, fade_out=fade_out_duration)
            current = out

        if progress_bar:
            out = _next_tmp()
            add_progress_bar(current, out, bar_height=bar_height)
            current = out

        if current != output_path:
            import shutil
            shutil.copy2(current, output_path)

        return output_path
    finally:
        for t in temps:
            Path(t).unlink(missing_ok=True)
        if tmp_dir.exists():
            try:
                tmp_dir.rmdir()
            except OSError:
                pass
