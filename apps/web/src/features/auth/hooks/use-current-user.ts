"use client";

import { useAuthStore } from "@/store/auth-store";
import type { UserResponse } from "../types";

/** Narrow selector for just the current user — components that only need this won't re-render on org/permission changes. */
export function useCurrentUser(): UserResponse | null {
  return useAuthStore((state) => state.user);
}
