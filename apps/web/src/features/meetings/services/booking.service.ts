import type { ApiResponse } from "@/types/api";
import { publicBookingClient } from "./public-booking-client";
import type { ConfirmBookingRequest, ConfirmBookingResponse, PublicBookingResponse } from "../types";

export async function getBookingSlots(bookingToken: string, signal?: AbortSignal): Promise<PublicBookingResponse> {
  const { data } = await publicBookingClient.get<ApiResponse<PublicBookingResponse>>(`/book/${bookingToken}`, {
    signal,
  });
  if (!data.data) throw new Error("This booking link is invalid or has expired.");
  return data.data;
}

export async function confirmBookingSlot(
  bookingToken: string,
  payload: ConfirmBookingRequest,
): Promise<ConfirmBookingResponse> {
  const { data } = await publicBookingClient.post<ApiResponse<ConfirmBookingResponse>>(
    `/book/${bookingToken}/confirm`,
    payload,
  );
  if (!data.data) throw new Error("Failed to confirm this booking.");
  return data.data;
}

export const bookingService = { getBookingSlots, confirmBookingSlot };
