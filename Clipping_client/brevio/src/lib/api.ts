import type {
  JobResponse,
  JobListResponse,
  JobCreateParams,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("brevio_token") : null;

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || "Something went wrong");
  }

  return res.json();
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  created_at: string;
}

export const api = {
  signup(email: string, password: string) {
    return request<TokenResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  login(email: string, password: string) {
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  me() {
    return request<UserResponse>("/auth/me");
  },

  health() {
    return request<{ status: string }>("/health");
  },

  createJob(file: File, params: JobCreateParams = {}) {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        query.set(key, String(value));
      }
    }

    const formData = new FormData();
    formData.append("video", file);

    const qs = query.toString();
    return request<JobResponse>(`/jobs${qs ? `?${qs}` : ""}`, {
      method: "POST",
      body: formData,
    });
  },

  listJobs() {
    return request<JobListResponse>("/jobs");
  },

  getJob(id: string) {
    return request<JobResponse>(`/jobs/${id}`);
  },

  getClipUrl(jobId: string, clipNumber: number) {
    return `${API_BASE}/jobs/${jobId}/clips/${clipNumber}`;
  },

  /** Same-origin URL for `<video>` playback (uses cookie via Next route). */
  getClipPlaybackUrl(jobId: string, clipNumber: number) {
    return `/api/jobs/${jobId}/clips/${clipNumber}`;
  },
};

export { ApiError };
