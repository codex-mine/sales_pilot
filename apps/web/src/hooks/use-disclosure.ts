"use client";

import { useCallback, useState } from "react";

export interface UseDisclosureReturn {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
  setOpen: (open: boolean) => void;
}

/** Boolean open/close state for dialogs, drawers, popovers, dropdowns. */
export function useDisclosure(initial = false): UseDisclosureReturn {
  const [isOpen, setIsOpen] = useState(initial);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  return { isOpen, open, close, toggle, setOpen: setIsOpen };
}
