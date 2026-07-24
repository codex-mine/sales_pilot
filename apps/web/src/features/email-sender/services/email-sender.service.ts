import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  CreateSenderMailboxRequest,
  EmailSenderConnectRequest,
  EmailSenderStatusResponse,
  SenderMailboxResponse,
  TestSmtpConnectionRequest,
  UpdateSenderMailboxRequest,
} from "../types";

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

// ─── Sender Mailbox Management (multi-mailbox) ────────────────────────────────────

export async function getSenderMailboxes(signal?: AbortSignal): Promise<SenderMailboxResponse[]> {
  const { data } = await apiClient.get<ApiResponse<SenderMailboxResponse[]>>("/settings/email-sender/mailboxes", { signal });
  return data.data ?? [];
}

export async function testSmtpConnection(payload: TestSmtpConnectionRequest): Promise<void> {
  await apiClient.post("/settings/email-sender/mailboxes/test-connection", payload);
}

export async function createSenderMailbox(payload: CreateSenderMailboxRequest): Promise<SenderMailboxResponse> {
  const { data } = await apiClient.post<ApiResponse<SenderMailboxResponse>>("/settings/email-sender/mailboxes", payload);
  if (!data.data) throw new Error("Failed to add sender mailbox.");
  return data.data;
}

export async function updateSenderMailbox(
  mailboxId: string,
  payload: UpdateSenderMailboxRequest,
): Promise<SenderMailboxResponse> {
  const { data } = await apiClient.patch<ApiResponse<SenderMailboxResponse>>(
    `/settings/email-sender/mailboxes/${mailboxId}`,
    payload,
  );
  if (!data.data) throw new Error("Failed to update sender mailbox.");
  return data.data;
}

export async function deleteSenderMailbox(mailboxId: string): Promise<void> {
  await apiClient.delete(`/settings/email-sender/mailboxes/${mailboxId}`);
}

export async function setDefaultSenderMailbox(mailboxId: string): Promise<SenderMailboxResponse> {
  const { data } = await apiClient.post<ApiResponse<SenderMailboxResponse>>(
    `/settings/email-sender/mailboxes/${mailboxId}/set-default`,
  );
  if (!data.data) throw new Error("Failed to set default mailbox.");
  return data.data;
}

export const emailSenderService = {
  getEmailSenderSettings,
  connectEmailSender,
  disconnectEmailSender,
  getSenderMailboxes,
  testSmtpConnection,
  createSenderMailbox,
  updateSenderMailbox,
  deleteSenderMailbox,
  setDefaultSenderMailbox,
};
