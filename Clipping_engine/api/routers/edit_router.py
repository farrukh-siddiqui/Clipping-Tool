"""Editor endpoints — filters, background music, and clip editing."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import Job, User, get_db
from api.models import (
    ClipMetadata,
    EditRequest,
    EditResponse,
    FilterInfo,
    MetadataResponse,
    MusicTrackInfo,
    VerticalResponse,
)
from engine.core.editor import FILTER_PRESETS, apply_edits
from engine.core.metadata import generate_clip_metadata
from engine.core.enhance import reframe_vertical

router = APIRouter(tags=["editor"])

JOBS_DIR = Path("jobs")
ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
MUSIC_DIR = ASSETS_DIR / "music"


def _load_music_catalog() -> list[dict]:
    catalog_path = MUSIC_DIR / "catalog.json"
    if not catalog_path.exists():
        return []
    with open(catalog_path) as f:
        return json.load(f)


def _find_music_file(music_id: str) -> Path | None:
    for track in _load_music_catalog():
        if track["id"] == music_id:
            p = MUSIC_DIR / track["file"]
            return p if p.exists() else None
    return None


# ── Asset listing ─────────────────────────────────────────────────────────────

@router.get("/assets/filters", response_model=List[FilterInfo])
def list_filters():
    """List available video filter presets."""
    return [
        FilterInfo(id=fid, name=preset["name"], description=preset["description"])
        for fid, preset in FILTER_PRESETS.items()
    ]


@router.get("/assets/music", response_model=List[MusicTrackInfo])
def list_music():
    """List available background music tracks."""
    catalog = _load_music_catalog()
    return [
        MusicTrackInfo(
            id=t["id"], name=t["name"], artist=t["artist"],
            duration_s=t["duration_s"], genre=t["genre"],
        )
        for t in catalog
        if (MUSIC_DIR / t["file"]).exists()
    ]


@router.get("/assets/music/{music_id}/preview")
def preview_music(music_id: str):
    """Stream a music track for preview playback."""
    path = _find_music_file(music_id)
    if not path:
        raise HTTPException(status_code=404, detail=f"Music track '{music_id}' not found")
    return FileResponse(str(path), media_type="audio/mpeg", filename=path.name)


# ── Clip editing ──────────────────────────────────────────────────────────────

def _get_completed_job(job_id: str, user: User, db: Session) -> Job:
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job is {job.status}, not completed")
    return job


@router.post("/jobs/{job_id}/clips/{clip_number}/edit", response_model=EditResponse)
async def edit_clip(
    job_id: str,
    clip_number: int,
    body: EditRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply a filter and/or background music to a completed clip."""
    job = _get_completed_job(job_id, current_user, db)

    if not body.filter_id and not body.music_id:
        raise HTTPException(status_code=400, detail="Provide at least filter_id or music_id")

    if body.filter_id and body.filter_id not in FILTER_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown filter: {body.filter_id}")

    original = JOBS_DIR / job_id / "outputs" / f"clip_{clip_number}.mp4"
    if not original.exists():
        raise HTTPException(status_code=404, detail=f"Clip {clip_number} not found")

    edited_path = JOBS_DIR / job_id / "outputs" / f"clip_{clip_number}_edited.mp4"

    music_path: str | None = None
    if body.music_id:
        mp = _find_music_file(body.music_id)
        if not mp:
            raise HTTPException(status_code=404, detail=f"Music track '{body.music_id}' not found or file missing")
        music_path = str(mp)

    await asyncio.to_thread(
        apply_edits,
        str(original),
        str(edited_path),
        filter_id=body.filter_id,
        music_path=music_path,
        music_volume=body.music_volume,
    )

    if not edited_path.exists() or edited_path.stat().st_size == 0:
        raise HTTPException(
            status_code=500,
            detail="Edit processing completed but output file is missing or empty",
        )

    _mark_clip_edited(job, clip_number, True, db)

    return EditResponse(
        clip_number=clip_number,
        edited=True,
        filter_id=body.filter_id,
        music_id=body.music_id,
    )


@router.delete("/jobs/{job_id}/clips/{clip_number}/edit", response_model=EditResponse)
def revert_clip(
    job_id: str,
    clip_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove edited version and revert to the original clip."""
    job = _get_completed_job(job_id, current_user, db)

    edited_path = JOBS_DIR / job_id / "outputs" / f"clip_{clip_number}_edited.mp4"
    if edited_path.exists():
        edited_path.unlink()

    _mark_clip_edited(job, clip_number, False, db)

    return EditResponse(clip_number=clip_number, edited=False)


def _mark_clip_edited(job: Job, clip_number: int, edited: bool, db: Session) -> None:
    """Update the edited flag in the job result JSON for a specific clip."""
    if not job.result:
        return
    result = json.loads(job.result)
    clips = result.get("clips", [])
    idx = clip_number - 1
    if 0 <= idx < len(clips):
        clips[idx]["edited"] = edited
        result["clips"] = clips
        job.result = json.dumps(result)
        db.commit()


def _get_clip_data(job: Job, clip_number: int) -> dict:
    """Extract a clip's metadata dict from the job result JSON."""
    if not job.result:
        raise HTTPException(status_code=400, detail="Job has no result data")
    result = json.loads(job.result)
    clips = result.get("clips", [])
    idx = clip_number - 1
    if idx < 0 or idx >= len(clips):
        raise HTTPException(status_code=404, detail=f"Clip {clip_number} not found in results")
    return clips[idx]


def _update_clip_field(job: Job, clip_number: int, field: str, value: Any, db: Session) -> None:
    """Set a field on a specific clip in the job result JSON."""
    result = json.loads(job.result)
    clips = result.get("clips", [])
    idx = clip_number - 1
    if 0 <= idx < len(clips):
        clips[idx][field] = value
        result["clips"] = clips
        job.result = json.dumps(result)
        db.commit()


# ── Metadata generation ──────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/clips/{clip_number}/metadata", response_model=MetadataResponse)
async def generate_metadata(
    job_id: str,
    clip_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate AI-powered title, description, tags, and hashtags for a clip."""
    job = _get_completed_job(job_id, current_user, db)
    clip_data = _get_clip_data(job, clip_number)

    transcript = clip_data.get("transcript_text", "")
    if not transcript:
        raise HTTPException(status_code=400, detail="Clip has no transcript text")

    raw = await asyncio.to_thread(
        generate_clip_metadata,
        transcript_text=transcript,
        hook_text=clip_data.get("hook_text", ""),
        video_filename=job.video_filename or "video",
        duration=clip_data.get("duration", 60.0),
        virality_score=clip_data.get("virality_score", 0),
        reason=clip_data.get("reason", clip_data.get("reason_short", "")),
    )

    metadata = {
        "title": raw["title"],
        "description": raw["description"],
        "tags": raw["tags"],
        "hashtags": raw["hashtags"],
    }

    _update_clip_field(job, clip_number, "social_metadata", metadata, db)

    return MetadataResponse(
        clip_number=clip_number,
        metadata=ClipMetadata(**metadata),
    )


@router.get("/jobs/{job_id}/clips/{clip_number}/metadata", response_model=MetadataResponse)
def get_metadata(
    job_id: str,
    clip_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get previously generated metadata for a clip."""
    job = _get_completed_job(job_id, current_user, db)
    clip_data = _get_clip_data(job, clip_number)

    saved = clip_data.get("social_metadata")
    if not saved:
        raise HTTPException(status_code=404, detail="No metadata generated yet")

    return MetadataResponse(
        clip_number=clip_number,
        metadata=ClipMetadata(**saved),
    )


# ── Vertical conversion ─────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/clips/{clip_number}/vertical", response_model=VerticalResponse)
async def convert_vertical(
    job_id: str,
    clip_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Convert a clip to 9:16 vertical format for Shorts/Reels/TikTok."""
    job = _get_completed_job(job_id, current_user, db)

    edited_path = JOBS_DIR / job_id / "outputs" / f"clip_{clip_number}_edited.mp4"
    original = JOBS_DIR / job_id / "outputs" / f"clip_{clip_number}.mp4"
    source = edited_path if edited_path.exists() else original

    if not source.exists():
        raise HTTPException(status_code=404, detail=f"Clip {clip_number} not found")

    vertical_path = JOBS_DIR / job_id / "outputs" / f"clip_{clip_number}_vertical.mp4"

    await asyncio.to_thread(reframe_vertical, str(source), str(vertical_path))

    return VerticalResponse(clip_number=clip_number, ready=True)


@router.get("/jobs/{job_id}/clips/{clip_number}/vertical")
def download_vertical(
    job_id: str,
    clip_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the vertical version of a clip."""
    job = _get_completed_job(job_id, current_user, db)

    vertical_path = JOBS_DIR / job_id / "outputs" / f"clip_{clip_number}_vertical.mp4"
    if not vertical_path.exists():
        raise HTTPException(status_code=404, detail="Vertical version not generated yet")

    return FileResponse(
        str(vertical_path),
        media_type="video/mp4",
        filename=f"clip_{clip_number}_vertical.mp4",
    )
