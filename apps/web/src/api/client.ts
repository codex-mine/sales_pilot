import axios, { AxiosHeaders } from "axios";
import { useAuthStore } from "@/store/auth-store";

const apiBaseUrl =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

const publicAuthEndpoints = [
  "/auth/login",
  "/auth/register",
  "/auth/forgot-password",
  "/auth/reset-password",
  "/auth/verify-email",
];

const apiClient = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const accessToken = useAuthStore.getState().accessToken;
  const requestUrl = config.url ?? "";
  const shouldAttachAuth = Boolean(
    accessToken &&
      !publicAuthEndpoints.some((endpoint) => requestUrl.includes(endpoint)),
  );

  if (shouldAttachAuth) {
    config.headers = new AxiosHeaders(config.headers);
    config.headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clearAuth();
    }

    return Promise.reject(error);
  },
);

export default apiClient;
