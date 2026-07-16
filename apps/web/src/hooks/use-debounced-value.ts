"use client";

import { useEffect, useState } from "react";

/** Returns a value that only updates after `delayMs` of no further changes. Used by SearchInput and filterable tables. */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timeout = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timeout);
  }, [value, delayMs]);

  return debounced;
}
