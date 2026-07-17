"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import { Building2, Trash2, Upload } from "@/icons";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { Spinner } from "@/components/ui/spinner";
import { getMediaUrl } from "@/lib/api/client";
import { useOrganizationLogo } from "../hooks/use-organization-logo";

const MAX_SIZE_MB = 5;
const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"];

export interface OrganizationLogoUploadProps {
  logoUrl: string | null;
  organizationName: string;
}

/** Upload / replace / delete the organization logo, with an instant local preview (before the upload even completes) and client-side validation that mirrors the backend's rules. */
export function OrganizationLogoUpload({
  logoUrl,
  organizationName,
}: OrganizationLogoUploadProps): React.ReactElement {
  const { uploadLogo, isUploading, removeLogo, isRemoving } = useOrganizationLogo();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const deleteConfirm = useConfirmDialog();

  function handleFileSelected(event: React.ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (!ACCEPTED_TYPES.includes(file.type)) {
      toast.error("Unsupported file type. Upload a PNG, JPEG, or WEBP image.");
      return;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      toast.error(`File too large. Maximum size is ${MAX_SIZE_MB}MB.`);
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    uploadLogo(file);
  }

  function handleDelete(): void {
    removeLogo();
    deleteConfirm.close();
  }

  const displayUrl = previewUrl ?? getMediaUrl(logoUrl);
  const isBusy = isUploading || isRemoving;

  return (
    <div className="flex items-center gap-4">
      <div className="relative">
        <Avatar
          size="xl"
          src={displayUrl}
          alt={organizationName}
          fallback={<Building2 className="size-6" />}
          className="rounded-xl"
        />
        {isBusy && (
          <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-overlay/40">
            <Spinner size="sm" className="text-white" />
          </div>
        )}
      </div>
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => inputRef.current?.click()}
            disabled={isBusy}
          >
            <Upload className="size-4" />
            {logoUrl ? "Replace logo" : "Upload logo"}
          </Button>
          {logoUrl && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={deleteConfirm.open}
              disabled={isBusy}
            >
              <Trash2 className="size-4" />
              Remove
            </Button>
          )}
        </div>
        <p className="text-caption text-muted-foreground">PNG, JPEG, or WEBP. Max {MAX_SIZE_MB}MB.</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(",")}
        onChange={handleFileSelected}
        className="sr-only"
      />
      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Remove organization logo?"
        description="This removes your organization's logo. You can upload a new one at any time."
        confirmLabel="Remove logo"
        isConfirming={isRemoving}
        onConfirm={handleDelete}
      />
    </div>
  );
}
