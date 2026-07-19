import { apiClient } from "@/lib/api/client";
import type { ApiResponse } from "@/types/api";
import type {
  CancelMeetingRequest,
  CreateMeetingRequest,
  LogMeetingOutcomeRequest,
  MeetingResponse,
  MeetingsQuery,
  PaginationMeta,
  ProposeTimesRequest,
  ProposeTimesResponse,
  RescheduleMeetingRequest,
} from "../types";

export async function getLeadMeetings(leadId: string, signal?: AbortSignal): Promise<MeetingResponse[]> {
  const { data } = await apiClient.get<ApiResponse<MeetingResponse[]>>(`/leads/${leadId}/meetings`, { signal });
  return data.data ?? [];
}

export async function createMeeting(leadId: string, payload: CreateMeetingRequest): Promise<MeetingResponse> {
  const { data } = await apiClient.post<ApiResponse<MeetingResponse>>(`/leads/${leadId}/meetings`, payload);
  if (!data.data) throw new Error("Failed to create meeting.");
  return data.data;
}

export async function getMeetings(
  query: MeetingsQuery = {},
  signal?: AbortSignal,
): Promise<{ meetings: MeetingResponse[]; meta: PaginationMeta }> {
  const { data } = await apiClient.get<ApiResponse<MeetingResponse[]>>("/meetings", { params: query, signal });
  return {
    meetings: data.data ?? [],
    meta: (data.meta as unknown as PaginationMeta) ?? { page: 1, page_size: 25, total: 0 },
  };
}

export async function proposeTimes(meetingId: string, payload: ProposeTimesRequest = {}): Promise<ProposeTimesResponse> {
  const { data } = await apiClient.post<ApiResponse<ProposeTimesResponse>>(
    `/meetings/${meetingId}/propose-times`,
    payload,
  );
  if (!data.data) throw new Error("Failed to propose times.");
  return data.data;
}

export async function rescheduleMeeting(meetingId: string, payload: RescheduleMeetingRequest): Promise<MeetingResponse> {
  const { data } = await apiClient.post<ApiResponse<MeetingResponse>>(`/meetings/${meetingId}/reschedule`, payload);
  if (!data.data) throw new Error("Failed to reschedule meeting.");
  return data.data;
}

export async function cancelMeeting(meetingId: string, payload: CancelMeetingRequest = {}): Promise<MeetingResponse> {
  const { data } = await apiClient.post<ApiResponse<MeetingResponse>>(`/meetings/${meetingId}/cancel`, payload);
  if (!data.data) throw new Error("Failed to cancel meeting.");
  return data.data;
}

export async function logMeetingOutcome(meetingId: string, payload: LogMeetingOutcomeRequest): Promise<MeetingResponse> {
  const { data } = await apiClient.post<ApiResponse<MeetingResponse>>(`/meetings/${meetingId}/outcome`, payload);
  if (!data.data) throw new Error("Failed to log outcome.");
  return data.data;
}

export const meetingService = {
  getLeadMeetings,
  createMeeting,
  getMeetings,
  proposeTimes,
  rescheduleMeeting,
  cancelMeeting,
  logMeetingOutcome,
};
