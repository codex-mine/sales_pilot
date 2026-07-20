"use client";

import { format } from "date-fns";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { CenteredLayout } from "@/components/layout/centered-layout";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, CheckCircle2, Clock, ExternalLink, Video } from "@/icons";
import { AuthCard } from "@/features/auth/components/auth-card";
import { useBookingSlots, useConfirmBookingSlot } from "@/features/meetings/hooks/use-booking";
import type { ConfirmBookingResponse, ProposedSlot } from "@/features/meetings/types";

export interface BookingPageContentProps {
  bookingToken: string;
}

/** Fully public — no auth guard, no cookie/session dependency, and calls a
 * separate credential-less client (see `public-booking-client.ts`). This is
 * the one page in the app a prospect with no account needs to reach and use,
 * and it must work well on a phone. */
export function BookingPageContent({ bookingToken }: BookingPageContentProps): React.ReactElement {
  const { booking, isLoading, isError, errorMessage } = useBookingSlots(bookingToken);
  const { confirmBookingSlot, isConfirming, errorMessage: confirmError } = useConfirmBookingSlot();
  const [confirmed, setConfirmed] = useState<ConfirmBookingResponse | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<ProposedSlot | null>(null);

  const groupedSlots = useMemo(() => {
    if (!booking) return [];
    const groups: { day: string; slots: ProposedSlot[] }[] = [];
    for (const slot of booking.proposed_times) {
      const day = format(new Date(slot.start), "EEEE, MMMM d");
      const existing = groups.find((group) => group.day === day);
      if (existing) existing.slots.push(slot);
      else groups.push({ day, slots: [slot] });
    }
    return groups;
  }, [booking]);

  async function handleConfirm(slot: ProposedSlot): Promise<void> {
    setSelectedSlot(slot);
    try {
      const result = await confirmBookingSlot({ bookingToken, payload: { start: slot.start, end: slot.end } });
      setConfirmed(result);
    } catch {
      // `confirmError` (from the mutation's own error state) already covers
      // user feedback — the selection stays so the failed slot is visible.
    }
  }

  return (
    <CenteredLayout maxWidthClassName="max-w-lg">
      <AuthCard
        title={confirmed ? "You're booked!" : (booking?.title ?? "Schedule a meeting")}
        description={
          confirmed
            ? undefined
            : booking?.host_name
              ? `with ${booking.host_name} at ${booking.organization_name}`
              : booking?.organization_name
        }
      >
        {isLoading ? (
          <div className="flex flex-col gap-3 p-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : isError || !booking ? (
          <EmptyState
            icon={AlertTriangle}
            title="This link is invalid or has expired"
            description={errorMessage ?? "Ask the sender for a new booking link."}
          />
        ) : confirmed ? (
          <div className="flex flex-col items-center gap-3 p-2 text-center">
            <CheckCircle2 className="size-8 text-success" />
            <p className="text-body-md font-medium text-foreground">{format(new Date(confirmed.scheduled_start), "PPPp")}</p>
            <p className="text-body-sm text-muted-foreground">A calendar invite has been sent to your email.</p>
            {confirmed.meeting_url && (
              <a
                href={confirmed.meeting_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 text-body-sm font-medium text-primary hover:underline"
              >
                <Video className="size-4" />
                Join with Google Meet
                <ExternalLink className="size-3" />
              </a>
            )}
          </div>
        ) : booking.status === "confirmed" ? (
          <EmptyState
            icon={CheckCircle2}
            title="This meeting is already booked"
            description={booking.scheduled_start ? format(new Date(booking.scheduled_start), "PPPp") : undefined}
          />
        ) : booking.status !== "proposed" ? (
          <EmptyState icon={AlertTriangle} title="This booking link is no longer open" />
        ) : groupedSlots.length === 0 ? (
          <EmptyState icon={Clock} title="No open times available" description="Ask the sender to propose new times." />
        ) : (
          <div className="flex flex-col gap-4 p-2">
            {booking.description && <p className="text-body-sm text-muted-foreground">{booking.description}</p>}
            <p className="text-caption text-muted-foreground">{booking.duration_minutes} minutes · pick a time below</p>
            {groupedSlots.map((group) => (
              <div key={group.day} className="flex flex-col gap-2">
                <p className="text-body-sm font-medium text-foreground">{group.day}</p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {group.slots.map((slot) => (
                    <Button
                      key={slot.start}
                      variant="outline"
                      size="sm"
                      isLoading={isConfirming && selectedSlot?.start === slot.start}
                      disabled={isConfirming}
                      onClick={() => void handleConfirm(slot)}
                    >
                      {format(new Date(slot.start), "p")}
                    </Button>
                  ))}
                </div>
              </div>
            ))}
            {confirmError && <p className="text-body-sm text-danger">{confirmError}</p>}
          </div>
        )}
      </AuthCard>
    </CenteredLayout>
  );
}
