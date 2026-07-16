/**
 * The envelope every API response follows (see the backend's
 * `app.schemas.common.ApiResponse`). Feature-specific payload shapes go in
 * `features/<name>/types`, not here — this file only holds the wrapper.
 */
export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  message: string;
  errors: Record<string, string[]> | null;
  meta: Record<string, unknown> | null;
}

/** A normalized, already-classified API error — see `lib/api/errors.ts`. */
export interface ApiErrorShape {
  status: number | null;
  code: string | null;
  message: string;
  fieldErrors: Record<string, string[]> | null;
  isNetworkError: boolean;
}
