"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Archive,
  ArchiveRestore,
  Building2,
  Globe,
  Linkedin,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Star,
  Trash2,
  Twitter,
} from "@/icons";
import { LeadMeetingsPanel } from "@/features/meetings/components/lead-meetings-panel";
import { getInitials } from "@/lib/utils";
import { useDeleteLead, useToggleLeadFlag } from "../hooks/use-lead-mutations";
import { useLead } from "../hooks/use-lead";
import { LEAD_STATUS_LABELS, type LeadStatus } from "../types";
import { LeadActivityTimeline } from "./lead-activity-timeline";
import { LeadAttachmentsPanel } from "./lead-attachments-panel";
import { LeadConversationsPanel } from "./lead-conversations-panel";
import { LeadFormDrawer } from "./lead-form-drawer";
import { LeadNotesPanel } from "./lead-notes-panel";
import { LeadOutreachPanel } from "./lead-outreach-panel";
import { LeadResearchPanel } from "./lead-research-panel";

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info" | "primary"> = {
  new: "info",
  researching: "info",
  research_done: "primary",
  contacted: "primary",
  opened: "primary",
  replied: "primary",
  qualified: "primary",
  interested: "primary",
  unqualified: "danger",
  demo_scheduled: "warning",
  proposal: "warning",
  negotiation: "warning",
  won: "success",
  lost: "danger",
  bounced: "danger",
  unsubscribed: "danger",
};

export interface LeadDetailContentProps {
  leadId: string;
}

export function LeadDetailContent({ leadId }: LeadDetailContentProps): React.ReactElement {
  const router = useRouter();
  const { lead, isLoading, isError, errorMessage, refetch } = useLead(leadId);
  const { toggleFavorite, toggleArchived } = useToggleLeadFlag();
  const { deleteLead, isDeleting } = useDeleteLead();
  const [isEditOpen, setIsEditOpen] = useState(false);
  const deleteConfirm = useConfirmDialog();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (isError || !lead) {
    return <ErrorState title="Couldn't load lead" description={errorMessage ?? undefined} onRetry={refetch} />;
  }

  async function handleDelete(): Promise<void> {
    await deleteLead(leadId);
    router.push("/leads");
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardContent className="flex flex-wrap items-start justify-between gap-4 pt-6">
          <div className="flex items-center gap-4">
            <Avatar size="xl" fallback={getInitials(lead.full_name)} />
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <h1 className="text-heading-4 font-semibold text-foreground">{lead.full_name}</h1>
                <StatusBadge tone={STATUS_TONE[lead.status] ?? "neutral"} pulse={lead.status === "researching"}>
                  {LEAD_STATUS_LABELS[lead.status as LeadStatus] ?? lead.status}
                </StatusBadge>
                {lead.is_archived && <Badge variant="outline">Archived</Badge>}
              </div>
              {lead.job_title && lead.company_name && (
                <p className="text-body-sm text-muted-foreground">
                  {lead.job_title} at {lead.company_name}
                </p>
              )}
              <div className="flex flex-wrap gap-1 pt-1">
                {lead.tags.map((tag) => (
                  <Badge key={tag.id} variant="soft">
                    {tag.name}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={lead.is_favorite ? "soft" : "outline"}
              size="sm"
              onClick={() => toggleFavorite(lead)}
            >
              <Star className="size-4" />
              {lead.is_favorite ? "Favorited" : "Favorite"}
            </Button>
            <Button variant="outline" size="sm" onClick={() => setIsEditOpen(true)}>
              <Pencil className="size-4" />
              Edit
            </Button>
            <Button variant="outline" size="sm" onClick={() => toggleArchived(lead)}>
              {lead.is_archived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
              {lead.is_archived ? "Restore" : "Archive"}
            </Button>
            <Button variant="danger" size="sm" onClick={deleteConfirm.open}>
              <Trash2 className="size-4" />
              Delete
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <Tabs defaultValue="notes">
            <TabsList>
              <TabsTrigger value="notes">Notes ({lead.notes_count})</TabsTrigger>
              <TabsTrigger value="research">Research</TabsTrigger>
              <TabsTrigger value="outreach">Outreach</TabsTrigger>
              <TabsTrigger value="conversations">Conversations</TabsTrigger>
              <TabsTrigger value="meetings">Meetings</TabsTrigger>
              <TabsTrigger value="attachments">Attachments ({lead.attachments_count})</TabsTrigger>
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
            </TabsList>
            <TabsContent value="notes">
              <Card>
                <CardContent className="pt-6">
                  <LeadNotesPanel leadId={lead.id} />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="research">
              <LeadResearchPanel leadId={lead.id} />
            </TabsContent>
            <TabsContent value="outreach">
              <LeadOutreachPanel leadId={lead.id} />
            </TabsContent>
            <TabsContent value="conversations">
              <Card>
                <CardContent className="pt-6">
                  <LeadConversationsPanel leadId={lead.id} />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="meetings">
              <Card>
                <CardContent className="pt-6">
                  <LeadMeetingsPanel leadId={lead.id} />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="attachments">
              <Card>
                <CardContent className="pt-6">
                  <LeadAttachmentsPanel leadId={lead.id} />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="timeline">
              <Card>
                <CardContent className="pt-6">
                  <LeadActivityTimeline leadId={lead.id} />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Contact</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <InfoRow icon={Mail} value={lead.email} href={lead.email ? `mailto:${lead.email}` : undefined} />
              <InfoRow icon={Phone} value={lead.phone} href={lead.phone ? `tel:${lead.phone}` : undefined} />
              <InfoRow icon={Globe} value={lead.website} href={lead.website ?? undefined} external />
              <InfoRow icon={Linkedin} value={lead.linkedin_url ? "LinkedIn" : null} href={lead.linkedin_url ?? undefined} external />
              <InfoRow icon={Twitter} value={lead.twitter_url ? "Twitter / X" : null} href={lead.twitter_url ?? undefined} external />
              <InfoRow
                icon={MapPin}
                value={[lead.city, lead.state, lead.country].filter(Boolean).join(", ") || null}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Company</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <InfoRow icon={Building2} value={lead.company_name} />
              <dl className="grid grid-cols-1 gap-3 text-body-sm sm:grid-cols-2">
                <div>
                  <dt className="text-caption text-muted-foreground">Industry</dt>
                  <dd className="text-foreground">{lead.industry || "—"}</dd>
                </div>
                <div>
                  <dt className="text-caption text-muted-foreground">Company size</dt>
                  <dd className="text-foreground">{lead.company_size || "—"}</dd>
                </div>
                <div>
                  <dt className="text-caption text-muted-foreground">Employees</dt>
                  <dd className="text-foreground">{lead.employee_count ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-caption text-muted-foreground">Revenue</dt>
                  <dd className="text-foreground">{lead.revenue != null ? `$${lead.revenue.toLocaleString()}` : "—"}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Score & priority</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-3 text-body-sm sm:grid-cols-2">
              <div>
                <dt className="text-caption text-muted-foreground">Lead score</dt>
                <dd className="text-heading-6 font-semibold text-foreground">{lead.lead_score ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-caption text-muted-foreground">Priority</dt>
                <dd className="text-heading-6 font-semibold text-foreground">{lead.priority}</dd>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Owner</CardTitle>
            </CardHeader>
            <CardContent>
              {lead.owner ? (
                <div className="flex items-center gap-2">
                  <Avatar size="sm" fallback={getInitials(lead.owner.full_name)} src={lead.owner.avatar_url ?? undefined} />
                  <div className="flex flex-col">
                    <span className="text-body-sm font-medium text-foreground">{lead.owner.full_name}</span>
                    <span className="text-caption text-muted-foreground">{lead.owner.email}</span>
                  </div>
                </div>
              ) : (
                <p className="text-body-sm text-muted-foreground">Unassigned</p>
              )}
            </CardContent>
          </Card>

          {lead.description && (
            <Card>
              <CardHeader>
                <CardTitle>Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-body-sm text-foreground">{lead.description}</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <LeadFormDrawer open={isEditOpen} onOpenChange={setIsEditOpen} lead={lead} />
      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Delete this lead?"
        description={`This permanently deletes "${lead.full_name}". This cannot be undone.`}
        confirmLabel="Delete lead"
        isConfirming={isDeleting}
        onConfirm={handleDelete}
      />
    </div>
  );
}

function InfoRow({
  icon: Icon,
  value,
  href,
  external,
}: {
  icon: typeof Mail;
  value: string | null | undefined;
  href?: string;
  external?: boolean;
}): React.ReactElement | null {
  if (!value) return null;
  const content = (
    <span className="flex items-center gap-2 text-body-sm text-foreground">
      <Icon className="size-4 shrink-0 text-muted-foreground" />
      <span className="truncate">{value}</span>
    </span>
  );
  if (!href) return content;
  return (
    <a
      href={href}
      target={external ? "_blank" : undefined}
      rel={external ? "noreferrer" : undefined}
      className="hover:underline"
    >
      {content}
    </a>
  );
}
