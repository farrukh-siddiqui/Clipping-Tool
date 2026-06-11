# Brevio — AI-Powered Long-Form to Short-Form Video Converter

Brevio takes long-form content (podcasts, interviews, streams, lectures) and automatically extracts the most viral-worthy moments as polished, platform-ready short-form clips for YouTube Shorts, TikTok, and Instagram Reels.

---

## What It Does

1. **Upload** a long-form video (any length)
2. **AI transcribes** every word with timestamps (OpenAI Whisper)
3. **AI ranks** the most compelling moments by virality, hook strength, curiosity, and standalone power (LLM via OpenRouter)
4. **Automatically cuts** each top clip, reorders the hook to play first, burns in animated captions, normalizes audio, and adds polish
5. **User reviews** clips with scores, transcripts, and hook highlights
6. **User edits** — apply color filters, add background music, convert to vertical 9:16
7. **AI generates** SEO-optimized titles, descriptions, tags, and hashtags for posting

The entire pipeline runs from a single video upload to download-ready clips with no manual editing required.

---

## Architecture

```
                                       JWT / REST
┌──────────────────────┐          ┌──────────────────────────────────┐
│   Brevio Frontend    │ ◄──────► │    Clipping Engine API           │
│   Next.js 16         │          │    FastAPI + Python              │
│   localhost:3000      │          │    localhost:8000                 │
└──────────────────────┘          └──────────┬───────────────────────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          │                  │                  │
                     Whisper            OpenRouter            FFmpeg
                  (local, on-device)   (cloud LLM API)    (all video/audio)
                   transcription      ranking + metadata   cut, filter, mix
```

### Why this setup

| Decision | Rationale |
|----------|-----------|
| **Two-port monolith** (3000 + 8000) | Simple to run locally; no Docker/K8s complexity for a tool that processes one video at a time |
| **No microservices for editing** | Filter and music operations are single FFmpeg calls on files already on disk — a separate service would add complexity without performance gain |
| **Background threads for pipeline** | Job submitted via POST returns 202 immediately; a daemon thread runs the pipeline; frontend polls for progress |
| **`asyncio.to_thread` for edits** | Short FFmpeg ops (5-10s) run in a thread pool so the event loop stays responsive |
| **SQLite** | Lightweight, zero-config, sufficient for single-server deployment |
| **Non-destructive edits** | Original `clip_N.mp4` is never overwritten; edited and vertical versions are separate files |
| **OpenRouter as LLM gateway** | Single API key for multiple models; automatic fallback from Gemini 2.5 Flash to Qwen3 32B |

---

## The 7-Stage Pipeline

When a user submits a video, the engine runs these stages sequentially:

```
Video Upload
    │
    ▼
┌─────────────────────────────────────────┐
│ Stage 1: Extract Audio                  │
│ FFmpeg strips audio → temp/audio.wav    │
│ (PCM s16le for Whisper)                 │
└───────────────┬─────────────────────────┘
                ▼
┌─────────────────────────────────────────┐
│ Stage 2: Transcribe                     │
│ OpenAI Whisper → timestamped segments   │
│ Outputs: segments.json                  │
└───────────────┬─────────────────────────┘
                ▼
┌─────────────────────────────────────────┐
│ Stage 3: Chunk Transcript               │
│ Group segments into ~60s windows        │
│ Outputs: chunks.json                    │
└───────────────┬─────────────────────────┘
                ▼
┌─────────────────────────────────────────┐
│ Stage 4: AI Ranking (LLM)              │
│ Full transcript → OpenRouter            │
│ Returns: top-K clips with virality      │
│ scores, hook text, reasons              │
│ Post-processing: sentence snapping,     │
│ deduplication, hook validation           │
│ Outputs: ranked_clips.json              │
└───────────────┬─────────────────────────┘
                ▼
┌─────────────────────────────────────────┐
│ Stages 5-7: Per-Clip Processing Loop   │
│                                         │
│ 5. Hook-First Assembly                  │
│    Reorder strongest sentence to start  │
│    (with guardrails to skip if unneeded)│
│                                         │
│ 6. Auto-Captions                        │
│    Generate styled ASS subtitles        │
│    Burn into video (CapCut-style)       │
│                                         │
│ 7. Enhancements                         │
│    Vertical reframe (optional)          │
│    EBU R128 loudness normalization      │
│    Fade in/out transitions              │
│    Animated progress bar                │
│                                         │
│ → Copy final to outputs/clip_N.mp4     │
└─────────────────────────────────────────┘
```

### AI Ranking — How Clips Are Scored

The LLM receives the **full transcript** with timestamps and selects the best moments. Each clip is scored on:

| Metric | What it measures |
|--------|-----------------|
| **Virality score** (1-100) | Overall viral potential |
| **Hook strength** (1-100) | How attention-grabbing the opening sentence is |
| **Standalone score** (1-100) | Whether the clip makes sense without context |
| **Curiosity score** (1-100) | How much it makes viewers want to keep watching |
| **Confidence** (1-100) | LLM's confidence in its own ranking |

Post-processing enforces sentence boundaries, rejects filler-word hooks ("so", "um", "like"), deduplicates overlapping clips, and ensures minimum quality thresholds.

### Hook-First Reordering

Inspired by how viral clips on TikTok/YouTube Shorts work — the most compelling sentence plays first, even if it originally appeared mid-clip. The engine:

1. Finds the hook timestamps in the transcript
2. Extracts the hook segment and body segment as separate cuts
3. Concatenates hook → body via FFmpeg concat demuxer

Guardrails prevent bad reorders (hook already near start, hook too far into clip, hook dominates clip duration).

---

## Post-Pipeline Editing

After the pipeline produces clips, users can apply additional edits without re-running anything.

### Video Filters

10 color-grading presets, all implemented as pure FFmpeg filter chains (no external LUT files):

| Filter | Effect |
|--------|--------|
| Warm | Golden tones, boosted saturation |
| Cool | Blue-shifted cool tones |
| Vintage | Faded retro film look |
| Cinematic | High contrast, desaturated film grade |
| Black & White | Classic monochrome |
| High Contrast | Punchy, vivid colors |
| Muted | Soft pastel desaturation |
| Vivid | Hyper-saturated bold colors |
| Film Grain | Analog noise overlay |
| Golden Hour | Warm sunset glow |

### Background Music

Copyright-free music tracks stored as `.mp3` assets, mixed under the original speech audio using FFmpeg's `amix` filter with adjustable volume (default 12%).

Current library: Inspiring Guitar, Greenland, Heroism, Voyager, Motivate — spanning motivational, cinematic, and epic genres.

### Vertical Conversion (9:16)

Converts landscape clips to portrait format for Shorts/Reels/TikTok using a blurred-background technique: the original video is scaled and centered with a Gaussian-blurred copy filling the 1080x1920 frame behind it.

---

## Social Media Metadata Generation

AI generates platform-ready metadata for each clip:

| Field | Spec |
|-------|------|
| **Title** | SEO-optimized, max 100 characters, no clickbait |
| **Description** | 2-3 sentences with CTA, max 500 characters |
| **Tags** | 8-15 YouTube tags (broad + niche mix) |
| **Hashtags** | 5-8 hashtags including #Shorts |

Users can **regenerate** if they don't like the result — each generation is a fresh LLM call. All metadata is copyable per-field from the UI.

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Register with email + password → JWT |
| POST | `/auth/login` | Login → JWT |
| GET | `/auth/me` | Get current user |

### Jobs (Pipeline)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/jobs` | Upload video + config → 202 Accepted, starts pipeline |
| GET | `/jobs` | List user's jobs |
| GET | `/jobs/{id}` | Job status, progress, results |
| GET | `/jobs/{id}/clips/{n}` | Download clip (serves edited version if available) |

### Editing

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/assets/filters` | List 10 filter presets |
| GET | `/assets/music` | List music tracks |
| GET | `/assets/music/{id}/preview` | Stream music for preview |
| POST | `/jobs/{id}/clips/{n}/edit` | Apply filter and/or music |
| DELETE | `/jobs/{id}/clips/{n}/edit` | Revert to original |

### Metadata & Conversion

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/jobs/{id}/clips/{n}/metadata` | Generate title/tags via AI |
| GET | `/jobs/{id}/clips/{n}/metadata` | Get saved metadata |
| POST | `/jobs/{id}/clips/{n}/vertical` | Convert to 9:16 |
| GET | `/jobs/{id}/clips/{n}/vertical` | Download vertical version |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

**Total: 17 authenticated endpoints + 4 public asset endpoints**

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Python 3, FastAPI, Uvicorn | REST API, async request handling |
| **Database** | SQLAlchemy + SQLite | Job and user persistence |
| **Auth** | python-jose (JWT) + passlib (bcrypt) | Token-based authentication |
| **Transcription** | OpenAI Whisper (local) | Speech-to-text with timestamps |
| **AI Ranking** | OpenRouter API (Gemini 2.5 Flash / Qwen3 32B) | Clip selection + metadata generation |
| **Video Processing** | FFmpeg + ffprobe | Every video operation (cut, filter, mix, reframe, captions) |
| **Subtitles** | pysubs2 | ASS subtitle generation |
| **Frontend** | Next.js 16, React 19, TypeScript | SSR + client-side app |
| **Styling** | Tailwind CSS 4, shadcn components | Dark-mode UI |
| **Animation** | Framer Motion | Page transitions and micro-interactions |
| **Icons** | Lucide React | Consistent icon set |

---

## Project Structure

```
Clipping Tool/
├── Clipping_engine/                    # Python backend
│   ├── api/
│   │   ├── main.py                     # FastAPI app entry
│   │   ├── models.py                   # Pydantic schemas
│   │   ├── database.py                 # SQLite models (User, Job)
│   │   ├── auth.py                     # JWT auth helpers
│   │   ├── worker.py                   # Background job runner
│   │   └── routers/
│   │       ├── auth_router.py          # Signup, login, me
│   │       ├── jobs_router.py          # Job CRUD + clip download
│   │       └── edit_router.py          # Filters, music, metadata, vertical
│   ├── engine/
│   │   ├── config.py                   # Global settings + env vars
│   │   ├── pipeline.py                 # 7-stage pipeline orchestrator
│   │   └── core/
│   │       ├── ffmpeg.py               # FFmpeg subprocess wrapper
│   │       ├── transcribe.py           # Whisper integration
│   │       ├── chunker.py              # Transcript windowing
│   │       ├── ranker.py               # LLM virality ranking
│   │       ├── cutter.py               # Stream-copy clip extraction
│   │       ├── hooks.py                # Hook-first reordering
│   │       ├── captions.py             # ASS subtitle generation + burn
│   │       ├── enhance.py              # Fade, loudness, vertical, progress bar
│   │       ├── editor.py               # Post-pipeline filters + BGM
│   │       └── metadata.py             # AI social media metadata
│   ├── assets/
│   │   ├── filters/catalog.json        # Filter preset metadata
│   │   └── music/                      # BGM tracks + catalog.json
│   ├── requirements.txt
│   └── scripts/                        # Test and utility scripts
│
├── Clipping_client/
│   └── brevio/                         # Next.js frontend
│       ├── src/
│       │   ├── app/
│       │   │   ├── page.tsx            # Landing page
│       │   │   ├── (auth)/             # Login + signup
│       │   │   └── dashboard/
│       │   │       ├── page.tsx         # Job list
│       │   │       ├── new/page.tsx     # 3-step job wizard
│       │   │       └── jobs/[id]/       # Job detail + clip cards
│       │   │           └── clips/[clipNumber]/edit/  # Clip editor
│       │   ├── components/             # UI components (landing, theme, shadcn)
│       │   └── lib/
│       │       ├── api.ts              # API client (all endpoints)
│       │       ├── types.ts            # TypeScript interfaces
│       │       ├── auth-context.tsx     # Auth state management
│       │       └── utils.ts            # Helpers (cn, timeAgo, formatDuration)
│       └── package.json
│
├── .gitignore
└── PROJECT.md                          # This file
```

---

## Job Storage

Each job gets an isolated directory:

```
jobs/{uuid}/
├── input.mp4                   # Uploaded source video
├── temp/
│   ├── audio.wav               # Extracted audio
│   ├── raw_clip_N.mp4          # Pre-enhancement cuts
│   ├── clip_N.ass              # Subtitle files
│   ├── captioned_clip_N.mp4    # After caption burn
│   └── enhanced_clip_N.mp4     # After enhancements
└── outputs/
    ├── segments.json            # Whisper transcript
    ├── chunks.json              # Grouped segments
    ├── ranked_clips.json        # LLM ranking results
    ├── clip_1.mp4               # Final clip (original)
    ├── clip_1_edited.mp4        # After filter/music (optional)
    └── clip_1_vertical.mp4      # 9:16 version (optional)
```

---

## Running Locally

### Prerequisites

- Python 3.10+
- Node.js 18+
- FFmpeg and ffprobe installed and on PATH
- OpenRouter API key ([get one here](https://openrouter.ai/keys))

### Backend

```bash
cd Clipping_engine
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Create .env
echo OPENROUTER_API_KEY=your_key_here > .env

uvicorn api.main:app --reload --port 8000
```

### Frontend

```bash
cd Clipping_client/brevio
npm install
npm run dev                    # localhost:3000
```

---

## User Flow

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Upload  │ ──► │Configure │ ──► │ Pipeline │ ──► │  Review  │
│  Video   │     │ Settings │     │ (auto)   │     │  Clips   │
└─────────┘     └──────────┘     └──────────┘     └────┬─────┘
                                                       │
                                          ┌────────────┼────────────┐
                                          ▼            ▼            ▼
                                     ┌─────────┐ ┌─────────┐ ┌──────────┐
                                     │  Edit   │ │ Generate │ │ Convert  │
                                     │ Filter  │ │ Title &  │ │  to 9:16 │
                                     │ + Music │ │  Tags    │ │          │
                                     └────┬────┘ └────┬────┘ └────┬─────┘
                                          │           │           │
                                          ▼           ▼           ▼
                                     ┌──────────────────────────────┐
                                     │     Download & Post          │
                                     │  (manual for now, auto later)│
                                     └──────────────────────────────┘
```

---

## What's Next

- **Automated social media posting** — direct upload to YouTube, TikTok, Instagram via their APIs
- **Batch editing** — apply the same filter/music across all clips in a job
- **Custom LUT support** — upload `.cube` files for brand-specific color grading
- **Clip preview before apply** — real-time filter preview in the browser
- **Multi-language support** — Whisper already supports 90+ languages; UI and metadata need localization
