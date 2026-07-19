"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { normalizeApiError } from "@/lib/api/errors";
import { meetingService } from "../services/meeting.service";
import type {
  CancelMeetingRequest,
  CreateMeetingRequest,
  LogMeetingOutcomeRequest,
  MeetingResponse,
  ProposeTimesRequest,
  ProposeTimesResponse,
  RescheduleMeetingRequest,
} from "../types";
import { LEAD_MEETINGS_QUERY_KEY } from "./use-lead-meetings";

function invalidateMeetingLists(queryClient: ReturnType<typeof useQueryClient>, leadId?: string): void {
  void queryClient.invalidateQueries({ queryKey: ["meetings", "list"] });
  if (leadId) void queryClient.invalidateQueries({ queryKey: LEAD_MEETINGS_QUERY_KEY(leadId) });
}

export interface UseCreateMeetingReturn {
  createMeeting: (args: { leadId: string; payload: CreateMeetingRequest }) => Promise<MeetingResponse>;
  isCreating: boolean;
}

export function useCreateMeeting(): UseCreateMeetingReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ leadId, payload }: { leadId: string; payload: CreateMeetingRequest }) =>
      meetingService.createMeeting(leadId, payload),
    onSuccess: (meeting) => {
      toast.success("Meeting created.");
      invalidateMeetingLists(queryClient, meeting.lead_id);
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { createMeeting: (args) => mutation.mutateAsync(args), isCreating: mutation.isPending };
}

export interface UseProposeTimesReturn {
  proposeTimes: (args: { meetingId: string; leadId?: string; payload?: ProposeTimesRequest }) => Promise<ProposeTimesResponse>;
  isProposing: boolean;
}

export function useProposeTimes(): UseProposeTimesReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ meetingId, payload }: { meetingId: string; leadId?: string; payload?: ProposeTimesRequest }) =>
      meetingService.proposeTimes(meetingId, payload),
    onSuccess: (result, variables) => {
      toast.success("Times proposed — share the booking link with your lead.");
      invalidateMeetingLists(queryClient, variables.leadId);
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { proposeTimes: (args) => mutation.mutateAsync(args), isProposing: mutation.isPending };
}

export interface UseRescheduleMeetingReturn {
  rescheduleMeeting: (args: { meetingId: string; leadId?: string; payload: RescheduleMeetingRequest }) => Promise<MeetingResponse>;
  isRescheduling: boolean;
}

export function useRescheduleMeeting(): UseRescheduleMeetingReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ meetingId, payload }: { meetingId: string; leadId?: string; payload: RescheduleMeetingRequest }) =>
      meetingService.rescheduleMeeting(meetingId, payload),
    onSuccess: (_meeting, variables) => {
      toast.success("Meeting rescheduled.");
      invalidateMeetingLists(queryClient, variables.leadId);
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { rescheduleMeeting: (args) => mutation.mutateAsync(args), isRescheduling: mutation.isPending };
}

export interface UseCancelMeetingReturn {
  cancelMeeting: (args: { meetingId: string; leadId?: string; payload?: CancelMeetingRequest }) => Promise<MeetingResponse>;
  isCancelling: boolean;
}

export function useCancelMeeting(): UseCancelMeetingReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ meetingId, payload }: { meetingId: string; leadId?: string; payload?: CancelMeetingRequest }) =>
      meetingService.cancelMeeting(meetingId, payload),
    onSuccess: (_meeting, variables) => {
      toast.success("Meeting cancelled.");
      invalidateMeetingLists(queryClient, variables.leadId);
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { cancelMeeting: (args) => mutation.mutateAsync(args), isCancelling: mutation.isPending };
}

export interface UseLogMeetingOutcomeReturn {
  logMeetingOutcome: (args: { meetingId: string; leadId?: string; payload: LogMeetingOutcomeRequest }) => Promise<MeetingResponse>;
  isLogging: boolean;
}

export function useLogMeetingOutcome(): UseLogMeetingOutcomeReturn {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ meetingId, payload }: { meetingId: string; leadId?: string; payload: LogMeetingOutcomeRequest }) =>
      meetingService.logMeetingOutcome(meetingId, payload),
    onSuccess: (_meeting, variables) => {
      toast.success("Outcome logged.");
      invalidateMeetingLists(queryClient, variables.leadId);
    },
    onError: (error) => toast.error(normalizeApiError(error).message),
  });
  return { logMeetingOutcome: (args) => mutation.mutateAsync(args), isLogging: mutation.isPending };
}
