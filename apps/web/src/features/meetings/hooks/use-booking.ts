"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { normalizeApiError } from "@/lib/api/errors";
import { bookingService } from "../services/booking.service";
import type { ConfirmBookingRequest, ConfirmBookingResponse, PublicBookingResponse } from "../types";

export const BOOKING_SLOTS_QUERY_KEY = (bookingToken: string) => ["booking", bookingToken] as const;

export interface UseBookingSlotsReturn {
  booking: PublicBookingResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
}

export function useBookingSlots(bookingToken: string): UseBookingSlotsReturn {
  const result = useQuery({
    queryKey: BOOKING_SLOTS_QUERY_KEY(bookingToken),
    queryFn: ({ signal }) => bookingService.getBookingSlots(bookingToken, signal),
    enabled: Boolean(bookingToken),
    retry: false,
  });

  return {
    booking: result.data,
    isLoading: result.isLoading,
    isError: result.isError,
    errorMessage: result.error ? normalizeApiError(result.error).message : null,
  };
}

export interface UseConfirmBookingSlotReturn {
  confirmBookingSlot: (args: { bookingToken: string; payload: ConfirmBookingRequest }) => Promise<ConfirmBookingResponse>;
  isConfirming: boolean;
  errorMessage: string | null;
}

export function useConfirmBookingSlot(): UseConfirmBookingSlotReturn {
  const mutation = useMutation({
    mutationFn: ({ bookingToken, payload }: { bookingToken: string; payload: ConfirmBookingRequest }) =>
      bookingService.confirmBookingSlot(bookingToken, payload),
  });
  return {
    confirmBookingSlot: (args) => mutation.mutateAsync(args),
    isConfirming: mutation.isPending,
    errorMessage: mutation.error ? normalizeApiError(mutation.error).message : null,
  };
}
