"use client";

import { useState, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";
import { Chip } from "./chip";

export interface TagInputProps {
  tags: string[];
  onTagsChange: (tags: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  /** Validates/transforms a candidate tag before it's added; return `null` to reject it. */
  parseTag?: (raw: string) => string | null;
  maxTags?: number;
}

const defaultParseTag = (raw: string): string | null => {
  const trimmed = raw.trim();
  return trimmed.length > 0 ? trimmed : null;
};

/** Free-text tag/chip entry — Enter or comma commits the current input as a tag (e.g. recipient lists, keywords). */
export function TagInput({
  tags,
  onTagsChange,
  placeholder = "Add a tag...",
  disabled,
  className,
  parseTag = defaultParseTag,
  maxTags,
}: TagInputProps): React.ReactElement {
  const [draft, setDraft] = useState("");

  const commit = (raw: string): void => {
    const parsed = parseTag(raw);
    if (!parsed || tags.includes(parsed)) return;
    if (maxTags && tags.length >= maxTags) return;
    onTagsChange([...tags, parsed]);
    setDraft("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>): void => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commit(draft);
    } else if (event.key === "Backspace" && draft.length === 0 && tags.length > 0) {
      onTagsChange(tags.slice(0, -1));
    }
  };

  return (
    <div
      className={cn(
        "flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-md border border-input bg-card px-2.5 py-1.5",
        "transition-colors duration-fast ease-standard focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
    >
      {tags.map((tag) => (
        <Chip key={tag} onRemove={disabled ? undefined : () => onTagsChange(tags.filter((t) => t !== tag))}>
          {tag}
        </Chip>
      ))}
      <input
        value={draft}
        disabled={disabled}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => draft && commit(draft)}
        placeholder={tags.length === 0 ? placeholder : undefined}
        className="min-w-24 flex-1 bg-transparent text-body-md outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
      />
    </div>
  );
}
