import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type { EmailSenderConnectRequest, EmailSenderStatusResponse } from "../types";

export async function getEmailSenderSettings(signal?: AbortSignal): Promise<EmailSenderStatusResponse> {
  const { data } = await apiClient.get<ApiResponse<EmailSenderStatusResponse>>("/settings/email-sender", { signal });
  if (!data.data) throw new Error("Sender settings not found.");
  return data.data;
}

export async function connectEmailSender(payload: EmailSenderConnectRequest): Promise<EmailSenderStatusResponse> {
  const { data } = await apiClient.post<ApiResponse<EmailSenderStatusResponse>>("/settings/email-sender", payload);
  if (!data.data) throw new Error("Connecting the sending mailbox failed.");
  return data.data;
}

export async function disconnectEmailSender(integrationId: string): Promise<void> {
  await apiClient.delete(`/settings/email-sender/${integrationId}`);
}

export const emailSenderService = {
  getEmailSenderSettings,
  connectEmailSender,
  disconnectEmailSender,
};
