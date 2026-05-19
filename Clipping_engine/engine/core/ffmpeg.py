import subprocess
from typing import List


def run_ffmpeg(command: List[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr.strip()}")
    return result.stdout


def extract_audio(input_video: str, output_audio: str) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_video,
        "-vn",
        "-acodec",
        "pcm_s16le",
        output_audio,
    ]
    run_ffmpeg(command)
