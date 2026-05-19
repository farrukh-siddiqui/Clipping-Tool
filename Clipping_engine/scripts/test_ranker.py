import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.core.ranker import rank_clips


def main() -> None:
    segments_path = ROOT_DIR / "outputs" / "segments.json"
    if not segments_path.exists():
        raise FileNotFoundError(
            "Missing outputs/segments.json — run the basic pipeline first "
            "to generate segments, or place a segments.json file manually."
        )

    segments = json.loads(segments_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(segments)} segments from {segments_path}")
    print()

    ranked = rank_clips(segments, top_k=3, clip_duration=60.0)

    print(f"\nLLM returned {len(ranked)} ranked clips:\n")
    for clip in ranked:
        print(f"  Rank {clip.get('rank', '?')}: "
              f"{clip['start']:.1f}s - {clip['end']:.1f}s "
              f"(score: {clip.get('virality_score', '?')})")
        print(f"    Hook:   {clip.get('hook_text', 'N/A')[:80]}")
        print(f"    Reason: {clip.get('reason', 'N/A')}")
        print()

    out_path = ROOT_DIR / "outputs" / "ranked_clips.json"
    out_path.write_text(json.dumps(ranked, indent=2), encoding="utf-8")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
