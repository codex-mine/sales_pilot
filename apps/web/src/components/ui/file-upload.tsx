"use client";

import { useCallback, useId, useRef, useState, type DragEvent } from "react";
import { File as FileIcon, Trash2, UploadCloud, X } from "@/icons";
import { cn } from "@/lib/utils";
import { IconButton } from "./icon-button";
import { Progress } from "./progress";

export interface FileUploadProps {
  onFilesAdded: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  maxSizeMb?: number;
  className?: string;
  label?: string;
  hint?: string;
}

/** A drag-and-drop file dropzone. Pairs with `FileUploadList`/`FileUploadItem` to render the resulting queue. */
export function FileUpload({
  onFilesAdded,
  accept,
  multiple = true,
  disabled = false,
  maxSizeMb,
  className,
  label = "Drag and drop files here",
  hint = "or click to browse",
}: FileUploadProps): React.ReactElement {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();

  const addFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList) return;
      let files = Array.from(fileList);
      if (maxSizeMb) files = files.filter((file) => file.size <= maxSizeMb * 1024 * 1024);
      if (files.length > 0) onFilesAdded(files);
    },
    [maxSizeMb, onFilesAdded],
  );

  const handleDrop = (event: DragEvent<HTMLDivElement>): void => {
    event.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    addFiles(event.dataTransfer.files);
  };

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
      }}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center",
        "transition-colors duration-fast ease-standard",
        isDragging ? "border-primary bg-accent" : "border-border bg-card hover:border-primary/50",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
    >
      <span className="flex size-11 items-center justify-center rounded-full bg-accent text-accent-foreground">
        <UploadCloud className="size-5" />
      </span>
      <div className="flex flex-col">
        <span className="text-body-sm font-medium text-foreground">{label}</span>
        <span className="text-body-sm text-muted-foreground">{hint}</span>
      </div>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        className="sr-only"
        onChange={(event) => {
          addFiles(event.target.files);
          event.target.value = "";
        }}
      />
    </div>
  );
}

export interface FileUploadItemProps {
  name: string;
  sizeLabel?: string;
  /** 0-100. Omit once the upload is complete. */
  progress?: number;
  status?: "uploading" | "complete" | "error";
  onRemove?: () => void;
  className?: string;
}

export function FileUploadItem({
  name,
  sizeLabel,
  progress,
  status = "uploading",
  onRemove,
  className,
}: FileUploadItemProps): React.ReactElement {
  return (
    <div className={cn("flex items-center gap-3 rounded-md border border-border bg-card p-3", className)}>
      <span
        className={cn(
          "flex size-9 shrink-0 items-center justify-center rounded-md",
          status === "error" ? "bg-danger-soft text-danger" : "bg-muted text-muted-foreground",
        )}
      >
        <FileIcon className="size-4" />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-body-sm font-medium text-foreground">{name}</span>
          {sizeLabel && <span className="shrink-0 text-caption text-muted-foreground">{sizeLabel}</span>}
        </div>
        {status === "uploading" && progress !== undefined && <Progress value={progress} className="h-1.5" />}
        {status === "error" && <span className="text-caption text-danger">Upload failed</span>}
      </div>
      {onRemove && (
        <IconButton
          icon={status === "complete" ? Trash2 : X}
          aria-label={status === "complete" ? "Remove file" : "Cancel upload"}
          variant="ghost"
          size="sm"
          onClick={onRemove}
        />
      )}
    </div>
  );
}
