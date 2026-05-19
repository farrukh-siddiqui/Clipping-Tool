from typing import Any, Dict, List


def create_chunks(
    segments: List[Dict[str, Any]], max_duration: float = 60.0
) -> List[Dict[str, Any]]:
    if not segments:
        return []

    chunks: List[Dict[str, Any]] = []
    current: List[Dict[str, Any]] = []
    start_time = float(segments[0]["start"])

    for seg in segments:
        current.append(seg)
        duration = float(seg["end"]) - start_time

        if duration >= max_duration:
            chunks.append(
                {
                    "start": start_time,
                    "end": float(seg["end"]),
                    "text": " ".join(str(s["text"]).strip() for s in current).strip(),
                }
            )
            current = []
            start_time = float(seg["end"])

    if current:
        chunks.append(
            {
                "start": start_time,
                "end": float(current[-1]["end"]),
                "text": " ".join(str(s["text"]).strip() for s in current).strip(),
            }
        )

    return chunks
