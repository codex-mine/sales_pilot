import apiClient from "@/api/client";
import type { ApiResponse } from "@/api/types";
import type { LoginRequest, LoginResponse, MeResponse } from "./types";

export async function login(payload: LoginRequest) {
  const { data } = await apiClient.post<ApiResponse<LoginResponse>>(
    "/auth/login",
    payload,
  );

  return data as ApiResponse<LoginResponse>;
}

export async function getCurrentUser() {
  const { data } = await apiClient.get<ApiResponse<MeResponse>>("/auth/me");
  return data as ApiResponse<MeResponse>;
}
