"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { LayoutGrid, Plus } from "@/icons";
import { WIDGET_DEFINITIONS } from "./widget-registry";

export interface AddWidgetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  visibleWidgetTypes: string[];
  onAdd: (widgetType: string) => void;
  isAdding: boolean;
}

export function AddWidgetDialog({ open, onOpenChange, visibleWidgetTypes, onAdd, isAdding }: AddWidgetDialogProps): React.ReactElement {
  const available = WIDGET_DEFINITIONS.filter((w) => !visibleWidgetTypes.includes(w.widgetType));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add widget</DialogTitle>
          <DialogDescription>Pick a widget to add to your dashboard.</DialogDescription>
        </DialogHeader>
        {available.length === 0 ? (
          <EmptyState icon={LayoutGrid} title="All widgets added" description="Every available widget is already on your dashboard." />
        ) : (
          <div className="flex flex-col gap-1">
            {available.map((widget) => (
              <button
                key={widget.widgetType}
                type="button"
                disabled={isAdding}
                onClick={() => onAdd(widget.widgetType)}
                className="flex items-center gap-3 rounded-lg border border-border p-3 text-left transition-colors hover:bg-muted/60 disabled:opacity-50"
              >
                <widget.icon className="size-4 shrink-0 text-muted-foreground" />
                <div className="flex min-w-0 flex-col">
                  <span className="text-body-sm font-medium text-foreground">{widget.title}</span>
                  <span className="text-caption text-muted-foreground">{widget.description}</span>
                </div>
                <Plus className="ml-auto size-4 shrink-0 text-muted-foreground" />
              </button>
            ))}
          </div>
        )}
        <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
          Close
        </Button>
      </DialogContent>
    </Dialog>
  );
}
