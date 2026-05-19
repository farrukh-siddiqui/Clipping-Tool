"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Plus,
  Video,
  Loader2,
  Clock,
  Film,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";
import { api, ApiError } from "@/lib/api";
import { cn, timeAgo } from "@/lib/utils";
import type { JobResponse, JobStatus } from "@/lib/types";

const statusConfig: Record<
  JobStatus,
  { label: string; className: string; icon: React.ElementType }
> = {
  pending: {
    label: "Pending",
    className: "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400",
    icon: Clock,
  },
  processing: {
    label: "Processing",
    className: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    icon: Loader2,
  },
  completed: {
    label: "Completed",
    className: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    className: "bg-red-500/10 text-red-600 dark:text-red-400",
    icon: AlertCircle,
  },
};

function JobCardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-card p-5 animate-pulse">
      <div className="flex items-start justify-between">
        <div className="space-y-2 flex-1">
          <div className="h-4 w-40 rounded bg-muted" />
          <div className="h-3 w-24 rounded bg-muted" />
        </div>
        <div className="h-5 w-20 rounded-full bg-muted" />
      </div>
      <div className="mt-4 flex gap-4">
        <div className="h-3 w-16 rounded bg-muted" />
        <div className="h-3 w-16 rounded bg-muted" />
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: JobStatus }) {
  const config = statusConfig[status];
  const Icon = config.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.className
      )}
    >
      <Icon
        className={cn(
          "size-3",
          status === "processing" && "animate-spin"
        )}
      />
      {config.label}
    </span>
  );
}

function JobCard({ job }: { job: JobResponse }) {
  const clipCount = job.result?.selected_clips ?? job.result?.clips?.length;

  return (
    <Link href={`/dashboard/jobs/${job.id}`}>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="group rounded-xl border border-border bg-card p-5 transition-all duration-200 hover:border-primary/30 hover:shadow-md hover:shadow-primary/5 hover:-translate-y-0.5 cursor-pointer"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Film className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="truncate font-medium text-sm">
                {job.video_filename}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {timeAgo(job.created_at)}
              </p>
            </div>
          </div>
          <StatusBadge status={job.status} />
        </div>

        <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
          {clipCount != null && (
            <span className="flex items-center gap-1">
              <Video className="size-3" />
              {clipCount} clip{clipCount !== 1 ? "s" : ""}
            </span>
          )}
          {job.progress && job.status === "processing" && (
            <span className="truncate">{job.progress}</span>
          )}
          {job.error && job.status === "failed" && (
            <span className="truncate text-red-500">{job.error}</span>
          )}
        </div>

        <div className="mt-3 flex items-center justify-end opacity-0 transition-opacity group-hover:opacity-100">
          <span className="flex items-center gap-1 text-xs font-medium text-primary">
            View details
            <ArrowRight className="size-3" />
          </span>
        </div>
      </motion.div>
    </Link>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const data = await api.listJobs();
      setJobs(data.jobs);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Failed to load jobs");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    const hasActive = jobs.some(
      (j) => j.status === "pending" || j.status === "processing"
    );
    if (!hasActive) return;
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [fetchJobs, jobs]);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold sm:text-3xl">Dashboard</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Welcome back{user?.email ? `, ${user.email}` : ""}
            </p>
          </div>
          <Button
            className="gap-2 bg-gradient-brand text-white hover:opacity-90"
            render={<Link href="/dashboard/new" />}
          >
            <Plus className="size-4" />
            New Job
          </Button>
        </div>

        <div className="mt-10">
          {loading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <JobCardSkeleton key={i} />
              ))}
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-destructive/30 py-16">
              <AlertCircle className="size-8 text-destructive" />
              <p className="mt-4 text-sm text-destructive">{error}</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => {
                  setLoading(true);
                  fetchJobs();
                }}
              >
                Retry
              </Button>
            </div>
          ) : jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border py-20">
              <div className="flex size-16 items-center justify-center rounded-2xl bg-muted">
                <Video className="size-7 text-muted-foreground" />
              </div>
              <h2 className="mt-5 text-lg font-semibold">No jobs yet</h2>
              <p className="mt-2 max-w-sm text-center text-sm text-muted-foreground">
                Upload a video and let AI extract the best clips automatically.
              </p>
              <Button
                className="mt-6 gap-2 bg-gradient-brand text-white hover:opacity-90"
                render={<Link href="/dashboard/new" />}
              >
                <Plus className="size-4" />
                Create Your First Job
              </Button>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {jobs.map((job, i) => (
                <motion.div
                  key={job.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.05 }}
                >
                  <JobCard job={job} />
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
