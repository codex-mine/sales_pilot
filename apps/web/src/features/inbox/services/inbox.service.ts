import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  ConversationDetailResponse,
  ConversationListItemResponse,
  ConversationsQuery,
  MessageResponse,
  PaginationMeta,
} from "../types";

export async function getConversations(
  query: ConversationsQuery = {},
  signal?: AbortSignal,
): Promise<{ conversations: ConversationListItemResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<ConversationListItemResponse[]>>("/inbox/conversations", {
    params: query,
    signal,
  });
  return {
    conversations: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

export async function getConversation(
  conversationId: string,
  signal?: AbortSignal,
): Promise<ConversationDetailResponse> {
  const { data } = await apiClient.get<ApiResponse<ConversationDetailResponse>>(
    `/inbox/conversations/${conversationId}`,
    { signal },
  );
  if (!data.data) throw new Error("Conversation not found.");
  return data.data;
}

export async function markConversationRead(
  conversationId: string,
  isRead: boolean,
): Promise<ConversationDetailResponse> {
  const { data } = await apiClient.patch<ApiResponse<ConversationDetailResponse>>(
    `/inbox/conversations/${conversationId}/read`,
    { is_read: isRead },
  );
  if (!data.data) throw new Error("Failed to update conversation.");
  return data.data;
}

export async function getMessage(messageId: string, signal?: AbortSignal): Promise<MessageResponse> {
  const { data } = await apiClient.get<ApiResponse<MessageResponse>>(`/inbox/messages/${messageId}`, { signal });
  if (!data.data) throw new Error("Message not found.");
  return data.data;
}

export async function reclassifyMessage(messageId: string, classification: string): Promise<MessageResponse> {
  const { data } = await apiClient.patch<ApiResponse<MessageResponse>>(
    `/inbox/messages/${messageId}/classification`,
    { classification },
  );
  if (!data.data) throw new Error("Failed to reclassify message.");
  return data.data;
}

export async function getLeadConversations(
  leadId: string,
  signal?: AbortSignal,
): Promise<ConversationListItemResponse[]> {
  const { data } = await apiClient.get<ApiResponse<ConversationListItemResponse[]>>(
    `/leads/${leadId}/conversations`,
    { signal },
  );
  return data.data ?? [];
}

export const inboxService = {
  getConversations,
  getConversation,
  markConversationRead,
  getMessage,
  reclassifyMessage,
  getLeadConversations,
};
