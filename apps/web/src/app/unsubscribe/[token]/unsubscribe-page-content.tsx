"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, MailX } from "@/icons";
import { Button } from "@/components/ui/button";
import { CenteredLayout } from "@/components/layout/centered-layout";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthCard } from "@/features/auth/components/auth-card";
import { apiClient } from "@/lib/api/client";
import { normalizeApiError } from "@/lib/api/errors";
import type { ApiResponse } from "@/types/api";

interface UnsubscribeInfo {
  lead_first_name: string | null;
  organization_name: string;
  already_unsubscribed: boolean;
}

interface UnsubscribeConfirmation {
  lead_first_name: string | null;
  organization_name: string;
}

async function getUnsubscribeInfo(token: string): Promise<UnsubscribeInfo> {
  const { data } = await apiClient.get<ApiResponse<UnsubscribeInfo>>(`/unsubscribe/${token}`);
  if (!data.data) throw new Error("This link is invalid or has expired.");
  return data.data;
}

async function confirmUnsubscribe(token: string): Promise<UnsubscribeConfirmation> {
  const { data } = await apiClient.post<ApiResponse<UnsubscribeConfirmation>>(`/unsubscribe/${token}`);
  if (!data.data) throw new Error("This link is invalid or has expired.");
  return data.data;
}

export interface UnsubscribePageContentProps {
  token: string;
}

/** Fully public — no auth guard, no cookie/session dependency. This is the
 * one page in the app a recipient with no account needs to reach and use. */
export function UnsubscribePageContent({ token }: UnsubscribePageContentProps): React.ReactElement {
  const [confirmed, setConfirmed] = useState(false);

  const info = useQuery({ queryKey: ["unsubscribe", token], queryFn: () => getUnsubscribeInfo(token) });
  const mutation = useMutation({
    mutationFn: () => confirmUnsubscribe(token),
    onSuccess: () => setConfirmed(true),
  });

  return (
    <CenteredLayout maxWidthClassName="max-w-sm">
      <AuthCard title="Unsubscribe">
        {info.isLoading ? (
          <div className="flex flex-col gap-3 p-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : info.isError || !info.data ? (
          <EmptyState
            icon={AlertTriangle}
            title="This link is invalid or has expired"
            description="If you're still receiving unwanted emails, contact the sender directly."
          />
        ) : confirmed || info.data.already_unsubscribed ? (
          <EmptyState
            icon={CheckCircle2}
            title="You're unsubscribed"
            description={`You won't receive further outreach emails from ${info.data.organization_name}.`}
          />
        ) : (
          <div className="flex flex-col items-center gap-4 p-2 text-center">
            <MailX className="size-8 text-muted-foreground" />
            <p className="text-body-sm text-foreground">
              {info.data.lead_first_name ? `Hi ${info.data.lead_first_name}, ` : ""}
              are you sure you want to unsubscribe from emails sent by{" "}
              <span className="font-medium">{info.data.organization_name}</span>?
            </p>
            <Button onClick={() => mutation.mutate()} isLoading={mutation.isPending} className="w-full">
              Confirm unsubscribe
            </Button>
            {mutation.isError && (
              <p className="text-body-sm text-danger">{normalizeApiError(mutation.error).message}</p>
            )}
          </div>
        )}
      </AuthCard>
    </CenteredLayout>
  );
}
