import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  ChangePasswordRequest,
  ForgotPasswordRequest,
  LoginRequest,
  MeResponse,
  RegisterRequest,
  ResetPasswordRequest,
  SessionResponse,
  TokenResponse,
  UserResponse,
  VerifyEmailRequest,
} from "../types";

/**
 * One function per backend endpoint, named to match. Every call unwraps to
 * `ApiResponse<T>["data"]` where the endpoint always returns data on success,
 * and to the full `ApiResponse<T>` where `meta` matters (e.g. the dev-only
 * `debug_reset_token`) or `data` is nullable by design (`logout`).
 *
 * Auth here is cookie-based — none of these need a manually-attached token;
 * `apiClient`'s `withCredentials: true` carries the httpOnly session cookies.
 */

export async function register(payload: RegisterRequest): Promise<ApiResponse<UserResponse>> {
  const { data } = await apiClient.post<ApiResponse<UserResponse>>("/auth/register", payload);
  return data;
}

export async function login(payload: LoginRequest): Promise<ApiResponse<UserResponse>> {
  const { data } = await apiClient.post<ApiResponse<UserResponse>>("/auth/login", payload);
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}

export async function logoutAll(): Promise<void> {
  await apiClient.post("/auth/logout-all");
}

export async function refresh(): Promise<ApiResponse<TokenResponse>> {
  const { data } = await apiClient.post<ApiResponse<TokenResponse>>("/auth/refresh");
  return data;
}

export async function me(signal?: AbortSignal): Promise<ApiResponse<MeResponse>> {
  const { data } = await apiClient.get<ApiResponse<MeResponse>>("/auth/me", { signal });
  return data;
}

export async function changePassword(payload: ChangePasswordRequest): Promise<void> {
  await apiClient.post("/auth/change-password", payload);
}

export async function forgotPassword(
  payload: ForgotPasswordRequest,
): Promise<ApiResponse<null>> {
  const { data } = await apiClient.post<ApiResponse<null>>("/auth/forgot-password", payload);
  return data;
}

export async function resetPassword(payload: ResetPasswordRequest): Promise<void> {
  await apiClient.post("/auth/reset-password", payload);
}

export async function verifyEmail(payload: VerifyEmailRequest): Promise<ApiResponse<UserResponse>> {
  const { data } = await apiClient.post<ApiResponse<UserResponse>>("/auth/verify-email", payload);
  return data;
}

export async function resendVerification(): Promise<ApiResponse<null>> {
  const { data } = await apiClient.post<ApiResponse<null>>("/auth/resend-verification");
  return data;
}

export async function getSessions(signal?: AbortSignal): Promise<SessionResponse[]> {
  const { data } = await apiClient.get<ApiResponse<SessionResponse[]>>("/auth/sessions", {
    signal,
  });
  return data.data ?? [];
}

export async function revokeSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/auth/sessions/${sessionId}`);
}

export const authService = {
  register,
  login,
  logout,
  logoutAll,
  refresh,
  me,
  changePassword,
  forgotPassword,
  resetPassword,
  verifyEmail,
  resendVerification,
  getSessions,
  revokeSession,
};
