"use client";

import { format } from "date-fns";
import { useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { CalendarDays, CheckCircle2, ExternalLink } from "@/icons";
import {
  useConnectGoogleCalendar,
  useDisconnectGoogleCalendar,
  useGoogleCalendarStatus,
} from "../hooks/use-calendar-integration";

const CALENDAR_ERROR_MESSAGES: Record<string, string> = {
  not_configured: "Google Calendar is not configured for this workspace yet — contact your administrator.",
  connection_failed: "We couldn't connect your Google Calendar. Please try again.",
};

export function CalendarIntegrationPanel(): React.ReactElement {
  const searchParams = useSearchParams();
  const { status, isLoading, refetch } = useGoogleCalendarStatus();
  const { connect } = useConnectGoogleCalendar();
  const { disconnect, isDisconnecting } = useDisconnectGoogleCalendar();
  const disconnectConfirm = useConfirmDialog();

  useEffect(() => {
    if (searchParams.get("calendar_connected")) {
      toast.success("Google Calendar connected.");
      void refetch();
    }
    const error = searchParams.get("calendar_error");
    if (error) {
      toast.error(CALENDAR_ERROR_MESSAGES[error] ?? "Something went wrong connecting Google Calendar.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fires once per redirect back from Google, not on every render
  }, [searchParams]);

  async function handleDisconnect(): Promise<void> {
    await disconnect();
    disconnectConfirm.close();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Calendar Integration</CardTitle>
        <CardDescription>
          Connect Google Calendar to propose open times to your leads and get meetings booked straight onto your
          calendar with a Google Meet link.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : status?.is_connected ? (
          <>
            <Alert variant="success" icon={CheckCircle2}>
              <AlertTitle>Connected</AlertTitle>
              <AlertDescription>
                {status.account_email}
                {status.connected_at && ` · connected ${format(new Date(status.connected_at), "PP")}`}
              </AlertDescription>
            </Alert>
            <div>
              <Button variant="outline" onClick={disconnectConfirm.open}>
                Disconnect Google Calendar
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center gap-3 rounded-lg border border-dashed border-border p-4">
              <Badge variant="outline">Not connected</Badge>
              <p className="text-body-sm text-muted-foreground">
                No calendar connected — you won&apos;t be able to propose meeting times until you connect one.
              </p>
            </div>
            <div>
              <Button onClick={connect}>
                <CalendarDays className="size-4" />
                Connect Google Calendar
                <ExternalLink className="size-4" />
              </Button>
            </div>
          </>
        )}
      </CardContent>

      <ConfirmDialog
        open={disconnectConfirm.isOpen}
        onOpenChange={disconnectConfirm.onOpenChange}
        title="Disconnect Google Calendar?"
        description="You won't be able to propose meeting times until you reconnect. Existing confirmed meetings are unaffected."
        confirmLabel="Disconnect"
        isConfirming={isDisconnecting}
        onConfirm={() => void handleDisconnect()}
      />
    </Card>
  );
}
