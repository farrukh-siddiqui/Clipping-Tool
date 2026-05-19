import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.pipeline import run_pipeline_basic as run_pipeline


def main() -> None:
    input_video = Path("Jim Rohn Motivation.mp4")
    if not input_video.exists():
        raise FileNotFoundError("Missing input video: Jim Rohn Motivation.mp4")

    result = run_pipeline(
        str(input_video),
        model_size="base",
        chunk_duration=60.0,
        top_k=2,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
