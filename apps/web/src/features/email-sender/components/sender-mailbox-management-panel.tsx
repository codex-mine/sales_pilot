"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { Mail, Pencil, Plus, Star, Trash2 } from "@/icons";
import { useDeleteSenderMailbox, useSenderMailboxes, useSetDefaultSenderMailbox } from "../hooks/use-sender-mailboxes";
import { ENCRYPTION_TYPE_LABELS, type EncryptionType, type SenderMailboxResponse } from "../types";
import { SenderMailboxFormDialog } from "./sender-mailbox-form-dialog";

/** Sender Mailbox Management — multi-mailbox list with add/edit/delete/set-
 * default. Every mailbox saved here was already verified by a real SMTP
 * connection test before it exists (see `EmailSenderSettingsService`), so
 * this list only ever shows mailboxes known to work at save time. */
export function SenderMailboxManagementPanel(): React.ReactElement {
  const { mailboxes, isLoading, isError, errorMessage, refetch } = useSenderMailboxes();
  const { deleteMailbox, isDeleting } = useDeleteSenderMailbox();
  const { setDefault, isSettingDefault } = useSetDefaultSenderMailbox();
  const [formOpen, setFormOpen] = useState(false);
  const [editingMailbox, setEditingMailbox] = useState<SenderMailboxResponse | undefined>(undefined);
  const [pendingDelete, setPendingDelete] = useState<SenderMailboxResponse | null>(null);
  const deleteConfirm = useConfirmDialog();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (isError) {
    return <ErrorState title="Couldn't load sender mailboxes" description={errorMessage ?? undefined} onRetry={refetch} />;
  }

  async function handleConfirmDelete(): Promise<void> {
    if (!pendingDelete) return;
    await deleteMailbox(pendingDelete.id);
    deleteConfirm.close();
    setPendingDelete(null);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-body-sm text-muted-foreground">
          {mailboxes.length} mailbox{mailboxes.length === 1 ? "" : "es"} configured.
        </p>
        <Button
          size="sm"
          onClick={() => {
            setEditingMailbox(undefined);
            setFormOpen(true);
          }}
        >
          <Plus className="size-4" />
          Add mailbox
        </Button>
      </div>

      {mailboxes.length === 0 ? (
        <EmptyState
          icon={Mail}
          title="No sender mailboxes configured"
          description="Add an SMTP mailbox to start sending campaign, AI-generated, and manual emails. The connection is verified before it's saved."
          action={
            <Button size="sm" onClick={() => setFormOpen(true)}>
              <Plus className="size-4" />
              Add mailbox
            </Button>
          }
        />
      ) : (
        <div className="flex flex-col gap-3">
          {mailboxes.map((mailbox) => (
            <Card key={mailbox.id}>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
                <div className="flex items-center gap-3">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-muted">
                    <Mail className="size-4 text-muted-foreground" />
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-body-sm font-medium text-foreground">{mailbox.name}</span>
                      {mailbox.is_default && (
                        <Badge variant="soft" size="sm">
                          <Star className="size-3" />
                          Default
                        </Badge>
                      )}
                      <StatusBadge tone={mailbox.is_active ? "success" : "neutral"}>
                        {mailbox.is_active ? "Active" : "Disabled"}
                      </StatusBadge>
                    </div>
                    <span className="text-caption text-muted-foreground">
                      {mailbox.email_address} · {mailbox.host}:{mailbox.port} ·{" "}
                      {ENCRYPTION_TYPE_LABELS[mailbox.encryption_type as EncryptionType] ?? mailbox.encryption_type}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {!mailbox.is_default && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void setDefault(mailbox.id)}
                      isLoading={isSettingDefault}
                    >
                      <Star className="size-4" />
                      Set default
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setEditingMailbox(mailbox);
                      setFormOpen(true);
                    }}
                  >
                    <Pencil className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-danger"
                    onClick={() => {
                      setPendingDelete(mailbox);
                      deleteConfirm.open();
                    }}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <SenderMailboxFormDialog open={formOpen} onOpenChange={setFormOpen} mailbox={editingMailbox} />
      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Delete this sender mailbox?"
        description={`"${pendingDelete?.name ?? "This mailbox"}" will no longer be usable for sending. Emails already sent through it keep their history.`}
        confirmLabel="Delete mailbox"
        isConfirming={isDeleting}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
