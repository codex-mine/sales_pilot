import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import type { ApiResponse } from "@/types/api";

/**
 * The one Axios instance for the whole app. Auth is cookie-based (httpOnly
 * `access_token` / `refresh_token`, set by the backend — see
 * `app/auth/cookies.py`), so `withCredentials: true` is what actually
 * authenticates requests; there is no token to read from JS for most calls.
 * The one exception is `POST /auth/refresh`, which *does* return a fresh
 * `access_token` in its JSON body (see `TokenResponse`) purely so non-browser
 * clients can use it — the browser flow never needs to read it, because the
 * refreshed cookie is already attached by the time the retried request goes
 * out. We still forward it onto `Authorization` defensively (see below) in
 * case a caller ever needs Bearer-style auth (e.g. a future public API
 * client), but nothing in this app depends on that path today.
 */

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(
  /\/$/,
  "",
);

// Endpoints that legitimately return 401 as a *result*, not as "your session
// expired" — a refresh attempt here would be pointless or actively wrong
// (e.g. retrying a refresh with the very refresh token that just failed).
const NO_REFRESH_RETRY_PATHS = [
  "/auth/login",
  "/auth/register",
  "/auth/refresh",
  "/auth/forgot-password",
  "/auth/reset-password",
  "/auth/verify-email",
  "/auth/resend-verification",
  "/organizations/invitations/accept",
];

declare module "axios" {
  export interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

let inMemoryAccessToken: string | null = null;

/** Called by the auth store whenever it obtains a fresh access token (login/refresh/register). */
export function setInMemoryAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (inMemoryAccessToken) {
    config.headers.set("Authorization", `Bearer ${inMemoryAccessToken}`);
  }
  return config;
});

// ─── 401 refresh-and-retry, with a queue so concurrent requests share one refresh ───

type QueuedRequest = { resolve: () => void; reject: (error: unknown) => void };

let isRefreshing = false;
let refreshQueue: QueuedRequest[] = [];

function flushQueue(error: unknown | null): void {
  refreshQueue.forEach(({ resolve, reject }) => (error ? reject(error) : resolve()));
  refreshQueue = [];
}

/** Set by the auth store on init so the interceptor can trigger a full logout on unrecoverable 401s. */
let onSessionExpired: (() => void) | null = null;
export function registerSessionExpiredHandler(handler: () => void): void {
  onSessionExpired = handler;
}

function isNoRefreshPath(url: string | undefined): boolean {
  if (!url) return false;
  return NO_REFRESH_RETRY_PATHS.some((path) => url.includes(path));
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiResponse<unknown>>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig | undefined;

    // Network error / timeout / cancellation — nothing to retry, just propagate.
    if (!error.response || !originalRequest) {
      return Promise.reject(error);
    }

    const status = error.response.status;

    if (status !== 401 || originalRequest._retry || isNoRefreshPath(originalRequest.url)) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    if (isRefreshing) {
      // A refresh is already in flight — queue this request behind it
      // instead of firing a second, redundant /auth/refresh call.
      return new Promise((resolve, reject) => {
        refreshQueue.push({
          resolve: () => resolve(apiClient(originalRequest)),
          reject,
        });
      });
    }

    isRefreshing = true;
    try {
      const { data } = await apiClient.post<ApiResponse<{ access_token: string }>>("/auth/refresh");
      if (data.data?.access_token) setInMemoryAccessToken(data.data.access_token);
      flushQueue(null);
      return apiClient(originalRequest);
    } catch (refreshError) {
      flushQueue(refreshError);
      setInMemoryAccessToken(null);
      onSessionExpired?.();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);
