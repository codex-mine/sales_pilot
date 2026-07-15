import type { AxiosError, InternalAxiosRequestConfig } from "axios";
import apiClient from "./client";

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    return Promise.reject(error);
  },
);

export const attachInterceptors = () => undefined;
