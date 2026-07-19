"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog, useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { IconButton } from "@/components/ui/icon-button";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronDown, ChevronUp, Clock3, Mail, Pencil, Sparkles, Trash2, Workflow } from "@/icons";
import { useCampaignSequence } from "../hooks/use-campaign-sequence";
import { useCreateSequence, useDeleteSequenceStep, useMoveSequenceStep } from "../hooks/use-sequence-mutations";
import { STEP_TYPE_LABELS, type SequenceStepResponse } from "../types";
import { SequenceStepFormDialog } from "./sequence-step-form-dialog";

const STEP_ICON: Record<string, typeof Mail> = { email: Mail, wait: Clock3, task: Clock3 };

export interface SequenceBuilderProps {
  campaignId: string;
}

export function SequenceBuilder({ campaignId }: SequenceBuilderProps): React.ReactElement {
  const { sequence, isLoading, refetch } = useCampaignSequence(campaignId);
  const { createSequence, isCreating } = useCreateSequence();
  const { moveStep } = useMoveSequenceStep();
  const { deleteStep, isDeleting } = useDeleteSequenceStep();
  const [stepDialogOpen, setStepDialogOpen] = useState(false);
  const [editingStep, setEditingStep] = useState<SequenceStepResponse | undefined>(undefined);
  const [pendingDeleteStep, setPendingDeleteStep] = useState<SequenceStepResponse | null>(null);
  const deleteConfirm = useConfirmDialog();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (!sequence) {
    return (
      <EmptyState
        icon={Workflow}
        title="No sequence yet"
        description="Create a sequence to define the steps leads will move through in this campaign."
        action={
          <Button
            size="sm"
            isLoading={isCreating}
            onClick={() =>
              void createSequence({ campaignId, payload: { name: "Main sequence" } })
                .then(() => refetch())
                .catch(() => {})
            }
          >
            Create sequence
          </Button>
        }
      />
    );
  }

  const steps = [...sequence.steps].sort((a, b) => a.step_order - b.step_order);
  const nextStepOrder = steps.length ? Math.max(...steps.map((s) => s.step_order)) + 1 : 1;

  async function handleConfirmDelete(): Promise<void> {
    if (!pendingDeleteStep) return;
    await deleteStep({ campaignId, stepId: pendingDeleteStep.id });
    deleteConfirm.close();
    setPendingDeleteStep(null);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-body-sm text-muted-foreground">{steps.length} step(s) in &ldquo;{sequence.name}&rdquo;</p>
        <Button
          size="sm"
          onClick={() => {
            setEditingStep(undefined);
            setStepDialogOpen(true);
          }}
        >
          Add step
        </Button>
      </div>

      {steps.length === 0 ? (
        <EmptyState icon={Workflow} title="No steps yet" description="Add the first step to this sequence." />
      ) : (
        <div className="flex flex-col gap-2">
          {steps.map((step, index) => {
            const Icon = STEP_ICON[step.step_type] ?? Mail;
            return (
              <Card key={step.id}>
                <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
                  <div className="flex items-center gap-3">
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-caption font-semibold text-foreground">
                      {index + 1}
                    </div>
                    <Icon className="size-4 text-muted-foreground" />
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-body-sm font-medium text-foreground">
                          {STEP_TYPE_LABELS[step.step_type as keyof typeof STEP_TYPE_LABELS] ?? step.step_type}
                        </span>
                        {step.step_type === "email" && step.content_source === "ai_personalized" && (
                          <Badge variant="soft">
                            <Sparkles className="size-3" />
                            AI-personalized
                          </Badge>
                        )}
                        {step.step_type === "email" && step.email_template && (
                          <Badge variant="outline">{step.email_template.name}</Badge>
                        )}
                        {step.condition?.skip_if && (
                          <Badge variant="outline">Skip if {step.condition.skip_if}</Badge>
                        )}
                      </div>
                      <span className="text-caption text-muted-foreground">
                        {step.delay_days > 0 || step.delay_hours > 0
                          ? `Waits ${step.delay_days > 0 ? `${step.delay_days}d ` : ""}${step.delay_hours > 0 ? `${step.delay_hours}h ` : ""}after the previous step`
                          : "Runs immediately after the previous step"}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <IconButton
                      icon={ChevronUp}
                      variant="ghost"
                      size="sm"
                      aria-label="Move up"
                      disabled={index === 0}
                      onClick={() => void moveStep({ campaignId, stepId: step.id, direction: "up" })}
                    />
                    <IconButton
                      icon={ChevronDown}
                      variant="ghost"
                      size="sm"
                      aria-label="Move down"
                      disabled={index === steps.length - 1}
                      onClick={() => void moveStep({ campaignId, stepId: step.id, direction: "down" })}
                    />
                    <IconButton
                      icon={Pencil}
                      variant="ghost"
                      size="sm"
                      aria-label="Edit step"
                      onClick={() => {
                        setEditingStep(step);
                        setStepDialogOpen(true);
                      }}
                    />
                    <IconButton
                      icon={Trash2}
                      variant="ghost"
                      size="sm"
                      aria-label="Delete step"
                      className="text-danger"
                      onClick={() => {
                        setPendingDeleteStep(step);
                        deleteConfirm.open();
                      }}
                    />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <SequenceStepFormDialog
        open={stepDialogOpen}
        onOpenChange={setStepDialogOpen}
        campaignId={campaignId}
        sequenceId={sequence.id}
        step={editingStep}
        nextStepOrder={nextStepOrder}
      />
      <ConfirmDialog
        open={deleteConfirm.isOpen}
        onOpenChange={deleteConfirm.onOpenChange}
        title="Delete this step?"
        description="This permanently removes the step from the sequence. Leads currently on this step will stall until the sequence is edited."
        confirmLabel="Delete step"
        isConfirming={isDeleting}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
