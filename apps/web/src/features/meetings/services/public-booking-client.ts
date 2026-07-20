import axios from "axios";

/**
 * A separate, credential-less Axios instance for the public booking page.
 * The prospect never has (or needs) a SalesPilot session — reusing the main
 * `apiClient` would attach cookies and route through its 401-refresh-retry
 * interceptor for no reason, since `/book/*` never requires or checks auth.
 */

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

export const publicBookingClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: false,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});
