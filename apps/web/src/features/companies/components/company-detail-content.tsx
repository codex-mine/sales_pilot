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
  DollarSign,
  Facebook,
  Globe,
  Instagram,
  Linkedin,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Trash2,
  Twitter,
} from "@/icons";
import { getInitials } from "@/lib/utils";
import { getMediaUrl } from "@/lib/api/client";
import { useCompany } from "../hooks/use-company";
import { useDeleteCompany, useToggleCompanyArchived } from "../hooks/use-company-mutations";
import { COMPANY_STATUS_LABELS, type CompanyStatus } from "../types";
import { CompanyActivityTimeline } from "./company-activity-timeline";
import { CompanyAttachmentsPanel } from "./company-attachments-panel";
import { CompanyEmployeesTable } from "./company-employees-table";
import { CompanyFormDrawer } from "./company-form-drawer";
import { CompanyLogoUpload } from "./company-logo-upload";
import { CompanyNotesPanel } from "./company-notes-panel";

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger" | "info" | "primary"> = {
  prospect: "info",
  active: "primary",
  customer: "success",
  partner: "primary",
  churned: "danger",
  inactive: "neutral",
};

export interface CompanyDetailContentProps {
  companyId: string;
}

export function CompanyDetailContent({ companyId }: CompanyDetailContentProps): React.ReactElement {
  const router = useRouter();
  const { company, isLoading, isError, errorMessage, refetch } = useCompany(companyId);
  const { toggleArchived } = useToggleCompanyArchived();
  const { deleteCompany, isDeleting } = useDeleteCompany();
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

  if (isError || !company) {
    return <ErrorState title="Couldn't load company" description={errorMessage ?? undefined} onRetry={refetch} />;
  }

  async function handleDelete(): Promise<void> {
    await deleteCompany(companyId);
    router.push("/companies");
  }

  const status = company.status as CompanyStatus;

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardContent className="flex flex-wrap items-start justify-between gap-4 pt-6">
          <div className="flex items-center gap-4">
            <Avatar
              size="xl"
              src={getMediaUrl(company.logo_url)}
              fallback={company.logo_url ? <Building2 className="size-6" /> : getInitials(company.name)}
              className="rounded-xl"
            />
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <h1 className="text-heading-4 font-semibold text-foreground">{company.name}</h1>
                <StatusBadge tone={STATUS_TONE[status] ?? "neutral"}>
                  {COMPANY_STATUS_LABELS[status] ?? status}
                </StatusBadge>
                {company.is_archived && <Badge variant="outline">Archived</Badge>}
              </div>
              {company.industry && <p className="text-body-sm text-muted-foreground">{company.industry}</p>}
              <div className="flex flex-wrap gap-1 pt-1">
                {company.tags.map((tag) => (
                  <Badge key={tag.id} variant="soft">
                    {tag.name}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setIsEditOpen(true)}>
              <Pencil className="size-4" />
              Edit
            </Button>
            <Button variant="outline" size="sm" onClick={() => toggleArchived(company)}>
              {company.is_archived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
              {company.is_archived ? "Restore" : "Archive"}
            </Button>
            <Button variant="danger" size="sm" onClick={deleteConfirm.open}>
              <Trash2 className="size-4" />
              Delete
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="employees">Employees ({company.contact_count})</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="notes">Notes ({company.notes_count})</TabsTrigger>
          <TabsTrigger value="attachments">Attachments ({company.attachments_count})</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Contact</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <InfoRow icon={Mail} value={company.email} href={company.email ? `mailto:${company.email}` : undefined} />
                <InfoRow icon={Phone} value={company.phone} href={company.phone ? `tel:${company.phone}` : undefined} />
                <InfoRow icon={Globe} value={company.website} href={company.website ?? undefined} external />
                <InfoRow icon={Linkedin} value={company.linkedin_url ? "LinkedIn" : null} href={company.linkedin_url ?? undefined} external />
                <InfoRow icon={Twitter} value={company.twitter_url ? "Twitter / X" : null} href={company.twitter_url ?? undefined} external />
                <InfoRow icon={Facebook} value={company.facebook_url ? "Facebook" : null} href={company.facebook_url ?? undefined} external />
                <InfoRow icon={Instagram} value={company.instagram_url ? "Instagram" : null} href={company.instagram_url ?? undefined} external />
                <InfoRow
                  icon={MapPin}
                  value={[company.address?.line1, company.city, company.state, company.country].filter(Boolean).join(", ") || null}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Company details</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-3 text-body-sm">
                  <div>
                    <dt className="text-caption text-muted-foreground">Legal name</dt>
                    <dd className="text-foreground">{company.legal_name || "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-caption text-muted-foreground">Founded</dt>
                    <dd className="text-foreground">{company.founded_year || "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-caption text-muted-foreground">Company size</dt>
                    <dd className="text-foreground">{company.size_range || "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-caption text-muted-foreground">Employees</dt>
                    <dd className="text-foreground">{company.employee_count ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-caption text-muted-foreground">Contacts on file</dt>
                    <dd className="text-foreground">{company.contact_count}</dd>
                  </div>
                  <div>
                    <dt className="text-caption text-muted-foreground">Leads</dt>
                    <dd className="text-foreground">{company.lead_count}</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Financials</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <InfoRow
                  icon={DollarSign}
                  value={
                    company.annual_revenue != null
                      ? `${company.currency} ${company.annual_revenue.toLocaleString()} / year`
                      : null
                  }
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Owner</CardTitle>
              </CardHeader>
              <CardContent>
                {company.owner ? (
                  <div className="flex items-center gap-2">
                    <Avatar size="sm" fallback={getInitials(company.owner.full_name)} src={company.owner.avatar_url ?? undefined} />
                    <div className="flex flex-col">
                      <span className="text-body-sm font-medium text-foreground">{company.owner.full_name}</span>
                      <span className="text-caption text-muted-foreground">{company.owner.email}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-body-sm text-muted-foreground">Unassigned</p>
                )}
              </CardContent>
            </Card>

            {company.description && (
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Description</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap text-body-sm text-foreground">{company.description}</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="employees">
          <Card>
            <CardContent className="pt-6">
              <CompanyEmployeesTable companyId={company.id} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="timeline">
          <Card>
            <CardContent className="pt-6">
              <CompanyActivityTimeline companyId={company.id} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notes">
          <Card>
            <CardContent className="pt-6">
              <CompanyNotesPanel companyId={company.id} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="attachments">
          <Card>
            <CardContent className="pt-6">
              <CompanyAttachmentsPanel companyId={company.id} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings">
          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Logo</CardTitle>
              </CardHeader>
              <CardContent>
                <CompanyLogoUpload companyId={company.id} logoUrl={company.logo_url} companyName={company.name} />
              </CardContent>
            </Card>

            <Card className="border-danger/40">
              <CardHeader>
                <CardTitle className="text-danger">Danger zone</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-body-sm font-medium text-foreground">
                    {company.is_archived ? "Restore this company" : "Archive this company"}
                  </p>
                  <p className="text-body-sm text-muted-foreground">
                    {company.is_archived
                      ? "This company is currently archived and hidden from the default list."
                      : "Archived companies are hidden from the default list but not deleted."}
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={() => toggleArchived(company)}>
                  {company.is_archived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
                  {company.is_archived ? "Restore" : "Archive"}
                </Button>
              </CardContent>
              <CardContent className="flex flex-wrap items-center justify-between gap-4 border-t border-border pt-4">
                <div>
                  <p className="text-body-sm font-medium text-foreground">Delete this company</p>
                  <p className="text-body-sm text-muted-foreground">This permanently deletes the company. This cannot be undone.</p>
                </div>
                <Button variant="danger" size="sm" onClick={deleteConfirm.open}>
                  <Trash2 className="size-4" />
                  Delete
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      <CompanyFormDrawer open={isEditOpen} onOpenChange={setIsEditOpen} company={company} />
      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Delete this company?"
        description={`This permanently deletes "${company.name}". This cannot be undone.`}
        confirmLabel="Delete company"
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
    <a href={href} target={external ? "_blank" : undefined} rel={external ? "noreferrer" : undefined} className="hover:underline">
      {content}
    </a>
  );
}
