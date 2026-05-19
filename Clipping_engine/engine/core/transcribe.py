from pathlib import Path
from typing import Any, Dict, List


def transcribe(audio_path: str, model_size: str = "base") -> List[Dict[str, Any]]:
    try:
        import whisper
    except ImportError as exc:
        raise ImportError(
            "Whisper is not installed. Run: pip install openai-whisper"
        ) from exc

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = whisper.load_model(model_size)
    result = model.transcribe(str(path))

    segments = result.get("segments", [])
    return [
        {
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "text": str(seg["text"]).strip(),
        }
        for seg in segments
    ]
