"""Job endpoints — submit, list, status, clip download."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import Job, User, get_db
from api.models import (
    JobCreateRequest,
    JobListResponse,
    JobResponse,
    JobResult,
)
from api.worker import run_job

router = APIRouter(prefix="/jobs", tags=["jobs"])

JOBS_DIR = Path("jobs")


def _job_to_response(job: Job) -> JobResponse:
    config = json.loads(job.config) if job.config else {}
    result = None
    if job.result:
        raw = json.loads(job.result)
        result = JobResult(**raw)

    return JobResponse(
        id=job.id,
        status=job.status,
        progress=job.progress,
        error=job.error,
        config=config,
        result=result,
        video_filename=job.video_filename,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.post("", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    video: UploadFile,
    top_k: int = 2,
    clip_duration: float = 60.0,
    model_size: str = "base",
    min_score: int = 40,
    llm_model: Optional[str] = None,
    enable_hooks: bool = True,
    enable_captions: bool = True,
    enable_enhancements: bool = True,
    vertical: bool = False,
    fade_in: float = 0.3,
    fade_out: float = 0.5,
    normalize_audio: bool = True,
    progress_bar: bool = True,
    caption_font: str = "Arial",
    caption_font_size: int = 22,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a new clipping job with a video file and configuration."""
    if not video.filename:
        raise HTTPException(status_code=400, detail="No video file provided")

    config = JobCreateRequest(
        top_k=top_k,
        clip_duration=clip_duration,
        model_size=model_size,
        min_score=min_score,
        llm_model=llm_model,
        enable_hooks=enable_hooks,
        enable_captions=enable_captions,
        enable_enhancements=enable_enhancements,
        vertical=vertical,
        fade_in=fade_in,
        fade_out=fade_out,
        normalize_audio=normalize_audio,
        progress_bar=progress_bar,
        caption_font=caption_font,
        caption_font_size=caption_font_size,
    )

    job = Job(
        user_id=current_user.id,
        video_filename=video.filename,
        config=config.model_dump_json(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    job_dir = JOBS_DIR / job.id
    job_dir.mkdir(parents=True, exist_ok=True)
    video_path = job_dir / "input.mp4"
    with open(video_path, "wb") as f:
        while chunk := video.file.read(1024 * 1024):
            f.write(chunk)

    thread = threading.Thread(
        target=run_job,
        args=(job.id, str(video_path), config.model_dump()),
        daemon=True,
    )
    thread.start()

    return _job_to_response(job)


@router.get("", response_model=JobListResponse)
def list_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(Job)
        .filter(Job.user_id == current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )
    return JobListResponse(jobs=[_job_to_response(j) for j in jobs])


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.get("/{job_id}/clips/{clip_number}")
def download_clip(
    job_id: str,
    clip_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a specific clip from a completed job."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job is {job.status}, not completed")

    edited_path = JOBS_DIR / job_id / "outputs" / f"clip_{clip_number}_edited.mp4"
    clip_path = JOBS_DIR / job_id / "outputs" / f"clip_{clip_number}.mp4"

    serve_path = edited_path if edited_path.exists() else clip_path
    if not serve_path.exists():
        raise HTTPException(status_code=404, detail=f"Clip {clip_number} not found")

    return FileResponse(
        path=str(serve_path),
        media_type="video/mp4",
        filename=f"clip_{clip_number}.mp4",
    )
