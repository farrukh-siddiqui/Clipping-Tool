"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  X,
  Film,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Check,
  Loader2,
  Scissors,
  Captions,
  Smartphone,
  Wand2,
  ArrowRight,
  Settings2,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { api, ApiError } from "@/lib/api";
import { cn, formatFileSize } from "@/lib/utils";
import type { JobCreateParams, WhisperModel } from "@/lib/types";

const STEPS = ["Upload", "Configure", "Review"] as const;

const WHISPER_MODELS: { value: WhisperModel; label: string; desc: string }[] = [
  { value: "tiny", label: "Tiny", desc: "Fastest, lower accuracy" },
  { value: "base", label: "Base", desc: "Good balance" },
  { value: "small", label: "Small", desc: "Better accuracy" },
  { value: "medium", label: "Medium", desc: "High accuracy" },
  { value: "large", label: "Large", desc: "Best accuracy, slowest" },
];

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center justify-center gap-2">
      {STEPS.map((step, i) => (
        <div key={step} className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "flex size-8 items-center justify-center rounded-full text-xs font-semibold transition-all",
                i < current
                  ? "bg-primary text-primary-foreground"
                  : i === current
                    ? "bg-primary text-primary-foreground glow"
                    : "bg-muted text-muted-foreground"
              )}
            >
              {i < current ? <Check className="size-4" /> : i + 1}
            </div>
            <span
              className={cn(
                "hidden text-sm font-medium sm:inline",
                i <= current
                  ? "text-foreground"
                  : "text-muted-foreground"
              )}
            >
              {step}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div
              className={cn(
                "h-px w-8 sm:w-12",
                i < current ? "bg-primary" : "bg-border"
              )}
            />
          )}
        </div>
      ))}
    </div>
  );
}

function ToggleSwitch({
  checked,
  onChange,
  label,
  description,
  icon: Icon,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description: string;
  icon: React.ElementType;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={cn(
        "flex items-start gap-3 rounded-xl border p-4 text-left transition-all",
        checked
          ? "border-primary/40 bg-primary/5"
          : "border-border bg-card hover:border-primary/20"
      )}
    >
      <div
        className={cn(
          "flex size-10 shrink-0 items-center justify-center rounded-lg transition-colors",
          checked ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"
        )}
      >
        <Icon className="size-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium">{label}</div>
        <div className="mt-0.5 text-xs text-muted-foreground">{description}</div>
      </div>
      <div
        className={cn(
          "mt-0.5 flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 transition-colors",
          checked ? "bg-primary" : "bg-muted"
        )}
      >
        <div
          className={cn(
            "size-4 rounded-full bg-white shadow-sm transition-transform",
            checked ? "translate-x-4" : "translate-x-0"
          )}
        />
      </div>
    </button>
  );
}

function RangeSlider({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  unit = "",
  displayValue,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  displayValue?: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <Label className="text-sm">{label}</Label>
        <span className="text-sm font-medium text-primary">
          {displayValue ?? `${value}${unit}`}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 rounded-full appearance-none cursor-pointer bg-muted accent-primary"
      />
      <div className="flex justify-between mt-1 text-[10px] text-muted-foreground">
        <span>{min}{unit}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  );
}

export default function NewJobPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [params, setParams] = useState<JobCreateParams>({
    top_k: 3,
    clip_duration: 60,
    model_size: "base",
    min_score: 40,
    enable_hooks: true,
    enable_captions: true,
    enable_enhancements: true,
    vertical: false,
    fade_in: 0.3,
    fade_out: 0.5,
    normalize_audio: true,
    progress_bar: true,
    caption_font: "Arial",
    caption_font_size: 22,
  });

  const updateParam = useCallback(
    <K extends keyof JobCreateParams>(key: K, value: JobCreateParams[K]) => {
      setParams((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const handleFile = useCallback((f: File) => {
    if (!f.type.startsWith("video/")) {
      setError("Please select a video file");
      return;
    }
    setFile(f);
    setError("");
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  async function handleSubmit() {
    if (!file) return;
    setSubmitting(true);
    setError("");

    try {
      const job = await api.createJob(file, {
        ...params,
        enable_captions: true,
        enable_enhancements: true,
      });
      router.push(`/dashboard/jobs/${job.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Failed to create job. Is the server running?");
      }
      setSubmitting(false);
    }
  }

  const canNext = step === 0 ? !!file : true;

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="mb-8 flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            render={<Link href="/dashboard" />}
          >
            <ChevronLeft className="size-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">New Clipping Job</h1>
            <p className="mt-0.5 text-sm text-muted-foreground">
              Upload a video and configure your clip settings
            </p>
          </div>
        </div>

        <StepIndicator current={step} />

        <div className="mt-8">
          <AnimatePresence mode="wait">
            {step === 0 && (
              <motion.div
                key="upload"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.25 }}
              >
                <div className="rounded-2xl border border-border bg-card p-6">
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Upload className="size-5 text-primary" />
                    Upload Your Video
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Drop a video file or click to browse. Supports MP4, MOV, AVI, MKV, and more.
                  </p>

                  <div
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={cn(
                      "mt-6 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-all",
                      dragOver
                        ? "border-primary bg-primary/5"
                        : file
                          ? "border-primary/30 bg-primary/5"
                          : "border-border hover:border-primary/30 hover:bg-muted/50"
                    )}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="video/*"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleFile(f);
                      }}
                    />

                    {file ? (
                      <div className="flex flex-col items-center gap-3">
                        <div className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                          <Film className="size-7" />
                        </div>
                        <div className="text-center">
                          <p className="font-medium text-sm">{file.name}</p>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            {formatFileSize(file.size)}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            setFile(null);
                          }}
                          className="gap-1 text-muted-foreground"
                        >
                          <X className="size-3" />
                          Remove
                        </Button>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-3">
                        <div className="flex size-14 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
                          <Upload className="size-7" />
                        </div>
                        <div className="text-center">
                          <p className="font-medium text-sm">
                            Drop your video here
                          </p>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            or click to browse files
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {step === 1 && (
              <motion.div
                key="configure"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.25 }}
                className="space-y-6"
              >
                <div className="rounded-2xl border border-border bg-card p-6">
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Scissors className="size-5 text-primary" />
                    Clip Settings
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    <strong className="text-foreground">Number of clips</strong> and{" "}
                    <strong className="text-foreground">max clip duration</strong> are sent to
                    the engine for chunking and AI ranking. Other options live under Features
                    and Advanced.
                  </p>

                  <div className="mt-6 space-y-6">
                    <RangeSlider
                      label="Number of Clips"
                      value={params.top_k!}
                      onChange={(v) => updateParam("top_k", v)}
                      min={1}
                      max={10}
                      displayValue={`${params.top_k} clip${params.top_k! > 1 ? "s" : ""}`}
                    />
                    <RangeSlider
                      label="Max Clip Duration"
                      value={params.clip_duration!}
                      onChange={(v) => updateParam("clip_duration", v)}
                      min={15}
                      max={120}
                      step={5}
                      unit="s"
                    />
                  </div>
                </div>

                <div className="rounded-2xl border border-border bg-card p-6">
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Sparkles className="size-5 text-primary" />
                    Features
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Hook order and layout are optional; captions and polish always run.
                  </p>

                  <div
                    className="mt-4 flex flex-col gap-3 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                    role="status"
                  >
                    <div className="flex items-start gap-3">
                      <Captions className="mt-0.5 size-5 shrink-0 text-primary" />
                      <div>
                        <p className="text-sm font-medium">Auto captions</p>
                        <p className="text-xs text-muted-foreground">
                          Burned-in subtitles — always on for every job.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 sm:border-l sm:border-border sm:pl-6">
                      <Sparkles className="mt-0.5 size-5 shrink-0 text-primary" />
                      <div>
                        <p className="text-sm font-medium">Production polish</p>
                        <p className="text-xs text-muted-foreground">
                          Fades, loudness, progress bar — always on.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 grid gap-3 sm:grid-cols-2">
                    <ToggleSwitch
                      checked={params.enable_hooks!}
                      onChange={(v) => updateParam("enable_hooks", v)}
                      label="Hook Reordering"
                      description="Place the strongest hook at the start of each clip"
                      icon={Wand2}
                    />
                    <ToggleSwitch
                      checked={params.vertical!}
                      onChange={(v) => updateParam("vertical", v)}
                      label="Vertical (9:16)"
                      description="Reframe for TikTok, Reels, and Shorts"
                      icon={Smartphone}
                    />
                  </div>
                </div>

                <div className="rounded-2xl border border-border bg-card overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="flex w-full items-center justify-between p-6 text-left"
                  >
                    <div className="flex items-center gap-2">
                      <Settings2 className="size-5 text-muted-foreground" />
                      <span className="text-sm font-medium">Advanced Settings</span>
                    </div>
                    <ChevronDown
                      className={cn(
                        "size-4 text-muted-foreground transition-transform",
                        showAdvanced && "rotate-180"
                      )}
                    />
                  </button>

                  <AnimatePresence>
                    {showAdvanced && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <Separator />
                        <div className="space-y-6 p-6">
                          <div>
                            <Label className="text-sm">Transcription model (Whisper)</Label>
                            <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-5">
                              {WHISPER_MODELS.map((m) => (
                                <button
                                  key={m.value}
                                  type="button"
                                  onClick={() => updateParam("model_size", m.value)}
                                  className={cn(
                                    "flex flex-col items-center rounded-lg border p-3 text-center transition-all",
                                    params.model_size === m.value
                                      ? "border-primary bg-primary/5 text-primary"
                                      : "border-border hover:border-primary/30",
                                  )}
                                >
                                  <span className="text-xs font-medium">{m.label}</span>
                                  <span className="mt-0.5 hidden text-[10px] text-muted-foreground sm:block">
                                    {m.desc}
                                  </span>
                                </button>
                              ))}
                            </div>
                          </div>
                          <RangeSlider
                            label="Minimum Virality Score"
                            value={params.min_score!}
                            onChange={(v) => updateParam("min_score", v)}
                            min={0}
                            max={100}
                          />
                          <div className="grid gap-4 sm:grid-cols-2">
                            <div>
                              <Label htmlFor="fade_in" className="text-sm">Fade In (seconds)</Label>
                              <Input
                                id="fade_in"
                                type="number"
                                min={0}
                                max={2}
                                step={0.1}
                                value={params.fade_in}
                                onChange={(e) => updateParam("fade_in", Number(e.target.value))}
                                className="mt-1.5"
                              />
                            </div>
                            <div>
                              <Label htmlFor="fade_out" className="text-sm">Fade Out (seconds)</Label>
                              <Input
                                id="fade_out"
                                type="number"
                                min={0}
                                max={2}
                                step={0.1}
                                value={params.fade_out}
                                onChange={(e) => updateParam("fade_out", Number(e.target.value))}
                                className="mt-1.5"
                              />
                            </div>
                          </div>
                          <div className="grid gap-4 sm:grid-cols-2">
                            <div>
                              <Label htmlFor="caption_font" className="text-sm">Caption Font</Label>
                              <Input
                                id="caption_font"
                                value={params.caption_font}
                                onChange={(e) => updateParam("caption_font", e.target.value)}
                                className="mt-1.5"
                              />
                            </div>
                            <div>
                              <Label htmlFor="caption_font_size" className="text-sm">Caption Font Size</Label>
                              <Input
                                id="caption_font_size"
                                type="number"
                                min={10}
                                max={72}
                                value={params.caption_font_size}
                                onChange={(e) => updateParam("caption_font_size", Number(e.target.value))}
                                className="mt-1.5"
                              />
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div
                key="review"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.25 }}
              >
                <div className="rounded-2xl border border-border bg-card p-6">
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Check className="size-5 text-primary" />
                    Review & Launch
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Confirm your settings before starting the clipping job
                  </p>

                  <div className="mt-6 space-y-4">
                    <div className="flex items-center gap-3 rounded-xl bg-muted/50 p-4">
                      <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Film className="size-5" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{file?.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {file && formatFileSize(file.size)}
                        </p>
                      </div>
                    </div>

                    <Separator />

                    <div className="grid gap-3 sm:grid-cols-2">
                      <ReviewRow label="Clips to extract" value={`${params.top_k}`} />
                      <ReviewRow label="Max duration" value={`${params.clip_duration}s`} />
                      <ReviewRow label="Transcription" value={params.model_size ?? "base"} />
                      <ReviewRow label="Min virality score" value={`${params.min_score}`} />
                      <ReviewRow label="Hook reordering" value={params.enable_hooks ? "On" : "Off"} />
                      <ReviewRow label="Auto captions" value="On (always)" />
                      <ReviewRow label="Production polish" value="On (always)" />
                      <ReviewRow label="Vertical (9:16)" value={params.vertical ? "On" : "Off"} />
                    </div>
                  </div>
                </div>

                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
                  >
                    {error}
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="mt-8 flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => setStep((s) => s - 1)}
            disabled={step === 0}
            className="gap-1"
          >
            <ChevronLeft className="size-4" />
            Back
          </Button>

          {step < 2 ? (
            <Button
              onClick={() => setStep((s) => s + 1)}
              disabled={!canNext}
              className="gap-1 bg-gradient-brand text-white hover:opacity-90"
            >
              Next
              <ChevronRight className="size-4" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={submitting}
              className="gap-2 bg-gradient-brand text-white hover:opacity-90"
            >
              {submitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  Start Clipping
                  <ArrowRight className="size-4" />
                </>
              )}
            </Button>
          )}
        </div>
      </motion.div>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-muted/30 px-3 py-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-xs font-medium capitalize">{value}</span>
    </div>
  );
}
