"use client";

import { useState } from "react";
import type { OrganizationMemberResponse } from "@/features/organizations/types";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getInitials } from "@/lib/utils";

export interface AssignOwnerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  members: OrganizationMemberResponse[];
  onAssign: (ownerId: string) => Promise<void>;
}

/** Owner picker reused for both single-lead and bulk owner assignment — the workspace member list comes from the existing Organization module (`useOrganizationMembers`), not a duplicate lookup. */
export function AssignOwnerDialog({ open, onOpenChange, members, onAssign }: AssignOwnerDialogProps): React.ReactElement {
  const [ownerId, setOwnerId] = useState<string>("");
  const [isAssigning, setIsAssigning] = useState(false);

  async function handleAssign(): Promise<void> {
    if (!ownerId) return;
    setIsAssigning(true);
    try {
      await onAssign(ownerId);
      setOwnerId("");
    } finally {
      setIsAssigning(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Assign owner</DialogTitle>
          <DialogDescription>Choose a workspace member to own the selected lead(s).</DialogDescription>
        </DialogHeader>
        <Select value={ownerId} onValueChange={setOwnerId}>
          <SelectTrigger>
            <SelectValue placeholder="Select a member" />
          </SelectTrigger>
          <SelectContent>
            {members.map((member) => (
              <SelectItem key={member.id} value={member.id}>
                <div className="flex items-center gap-2">
                  <Avatar size="xs" fallback={getInitials(member.full_name)} />
                  {member.full_name}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={handleAssign} isLoading={isAssigning} disabled={!ownerId}>
            Assign
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
