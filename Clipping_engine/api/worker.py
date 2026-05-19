"""Background pipeline runner — executes jobs in isolated directories."""

from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

import engine.config as engine_cfg
from api.database import Job, SessionLocal
from engine.pipeline import run_pipeline


def run_job(job_id: str, video_path: str, config: dict) -> None:
    """Run the full clipping pipeline for a job.

    Temporarily overrides engine TEMP_DIR / OUTPUTS_DIR so each job
    writes to its own ``jobs/<id>/`` directory, then restores the
    originals when done.
    """
    job_dir = Path(f"jobs/{job_id}")
    temp_dir = job_dir / "temp"
    outputs_dir = job_dir / "outputs"
    temp_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    orig_temp = engine_cfg.TEMP_DIR
    orig_outputs = engine_cfg.OUTPUTS_DIR

    db = SessionLocal()

    def report_progress(message: str) -> None:
        j = db.query(Job).filter(Job.id == job_id).first()
        if j:
            j.progress = message
            db.commit()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        job.status = "processing"
        job.progress = "Stage 1/7: Queued — starting pipeline..."
        db.commit()

        engine_cfg.TEMP_DIR = temp_dir
        engine_cfg.OUTPUTS_DIR = outputs_dir

        clip_dur = float(config.get("clip_duration", 60.0))

        result = run_pipeline(
            video_path,
            model_size=config.get("model_size", "base"),
            chunk_duration=clip_dur,
            top_k=config.get("top_k", 2),
            clip_duration=clip_dur,
            llm_model=config.get("llm_model"),
            min_score=config.get("min_score", 40),
            enable_hooks=config.get("enable_hooks", True),
            enable_captions=True,
            enable_enhancements=True,
            vertical=config.get("vertical", False),
            on_progress=report_progress,
        )

        clip_results = []
        for clip in result.get("clips", []):
            clip_results.append({
                "path": clip.get("path", ""),
                "start": clip.get("start", 0),
                "end": clip.get("end", 0),
                "duration": clip.get("duration", 0),
                "virality_score": clip.get("virality_score"),
                "confidence": clip.get("confidence"),
                "hook_strength": clip.get("hook_strength"),
                "standalone_score": clip.get("standalone_score"),
                "curiosity_score": clip.get("curiosity_score"),
                "reason": clip.get("reason", ""),
                "reason_short": clip.get("reason_short"),
                "hook_text": clip.get("hook_text", ""),
                "transcript_text": clip.get("transcript_text", ""),
            })

        job_result = {
            "total_segments": result.get("total_segments", 0),
            "total_chunks": result.get("total_chunks", 0),
            "selected_clips": result.get("selected_clips", 0),
            "clips": clip_results,
        }

        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "completed"
            job.progress = "Done"
            job.result = json.dumps(job_result)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

    except Exception:
        tb = traceback.format_exc()
        print(f"[worker] Job {job_id} failed:\n{tb}")
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = tb[-2000:]
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        engine_cfg.TEMP_DIR = orig_temp
        engine_cfg.OUTPUTS_DIR = orig_outputs
        db.close()
