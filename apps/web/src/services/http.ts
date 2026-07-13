import axios, { type InternalAxiosRequestConfig } from "axios";
const client = axios.create({ baseURL: process.env.NEXT_PUBLIC_API_URL, withCredentials: true, headers: { "Content-Type": "application/json" } });
client.interceptors.request.use((config: InternalAxiosRequestConfig) => config);
client.interceptors.response.use((response) => response, async (error: unknown) => Promise.reject(error));
// Refresh tokens live in secure HttpOnly cookies; retry orchestration belongs here when API auth is connected.
export default client;
