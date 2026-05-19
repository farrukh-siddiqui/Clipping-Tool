from .ffmpeg import run_ffmpeg

from engine.config import TAIL_PAD_MS


def cut_clip(
    input_video: str,
    start: float,
    end: float,
    output_path: str,
    *,
    tail_pad_ms: int = TAIL_PAD_MS,
) -> None:
    """Cut a clip from the source video with a small tail pad.

    ``tail_pad_ms`` adds breathing room after the last word so it
    doesn't get clipped.
    """
    padded_end = end + tail_pad_ms / 1000.0

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-to",
        str(padded_end),
        "-i",
        input_video,
        "-c",
        "copy",
        output_path,
    ]
    run_ffmpeg(command)
