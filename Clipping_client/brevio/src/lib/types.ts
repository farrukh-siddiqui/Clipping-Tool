export type JobStatus = "pending" | "processing" | "completed" | "failed";

export type WhisperModel = "tiny" | "base" | "small" | "medium" | "large";

export interface ClipResult {
  path: string;
  start: number;
  end: number;
  duration: number;
  virality_score: number | null;
  confidence: number | null;
  hook_strength: number | null;
  standalone_score: number | null;
  curiosity_score: number | null;
  reason: string | null;
  reason_short: string | null;
  hook_text: string | null;
  transcript_text: string | null;
  edited?: boolean;
}

export interface JobResult {
  total_segments: number;
  total_chunks: number;
  selected_clips: number;
  clips: ClipResult[];
}

export interface JobResponse {
  id: string;
  status: JobStatus;
  progress: string | null;
  error: string | null;
  config: Record<string, unknown>;
  result: JobResult | null;
  video_filename: string;
  created_at: string;
  completed_at: string | null;
}

export interface JobListResponse {
  jobs: JobResponse[];
}

export interface FilterPreset {
  id: string;
  name: string;
  description: string;
}

export interface MusicTrack {
  id: string;
  name: string;
  artist: string;
  duration_s: number;
  genre: string;
}

export interface ClipMetadata {
  title: string;
  description: string;
  tags: string[];
  hashtags: string[];
}

export interface MetadataResponse {
  clip_number: number;
  metadata: ClipMetadata;
}

export interface VerticalResponse {
  clip_number: number;
  ready: boolean;
}

export interface EditClipParams {
  filter_id?: string | null;
  music_id?: string | null;
  music_volume?: number;
}

export interface EditClipResponse {
  clip_number: number;
  edited: boolean;
  filter_id: string | null;
  music_id: string | null;
}

export interface JobCreateParams {
  top_k?: number;
  clip_duration?: number;
  model_size?: WhisperModel;
  min_score?: number;
  llm_model?: string;
  enable_hooks?: boolean;
  enable_captions?: boolean;
  enable_enhancements?: boolean;
  vertical?: boolean;
  fade_in?: number;
  fade_out?: number;
  normalize_audio?: boolean;
  progress_bar?: boolean;
  caption_font?: string;
  caption_font_size?: number;
}
