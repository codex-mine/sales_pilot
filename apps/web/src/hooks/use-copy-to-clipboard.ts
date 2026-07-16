"use client";

import { useCallback, useState } from "react";

/** Copies text to the clipboard and exposes a transient `copied` flag (resets after 2s) for UI feedback. */
export function useCopyToClipboard(resetDelayMs = 2000): {
  copied: boolean;
  copy: (text: string) => Promise<void>;
} {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(
    async (text: string) => {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), resetDelayMs);
    },
    [resetDelayMs],
  );

  return { copied, copy };
}
