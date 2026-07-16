import axios from "axios";
import type { ApiErrorShape, ApiResponse } from "@/types/api";

/**
 * Normalizes anything thrown by the API client into one shape the rest of
 * the app can branch on, regardless of whether it was an Axios error, a
 * network failure, or something unexpected.
 *
 * The backend's error envelope (see `app.exceptions.handlers`) is:
 *   { success: false, message: "...", errors: { "<field-or-error_code>": ["..."] } }
 * - Validation failures (422) key `errors` by form field name.
 * - App-level failures (401/403/404/409/423/429) key it by `"error_code"`,
 *   holding one machine-readable slug (`invalid_credentials`,
 *   `permission_denied`, `account_locked`, ...) — pull that out as `code` so
 *   callers can branch on it without string-matching `message`.
 */
export function normalizeApiError(error: unknown): ApiErrorShape {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return {
        status: null,
        code: error.code === "ERR_CANCELED" ? "request_cancelled" : "network_error",
        message:
          error.code === "ERR_CANCELED"
            ? "Request was cancelled."
            : "We couldn't reach the server. Check your connection and try again.",
        fieldErrors: null,
        isNetworkError: error.code !== "ERR_CANCELED",
      };
    }

    const body = error.response.data as ApiResponse<unknown> | undefined;
    const fieldErrors = body?.errors ?? null;
    const code = fieldErrors?.error_code?.[0] ?? null;

    return {
      status: error.response.status,
      code,
      message: body?.message || fallbackMessageForStatus(error.response.status),
      fieldErrors,
      isNetworkError: false,
    };
  }

  return {
    status: null,
    code: "unknown_error",
    message: "Something unexpected happened. Please try again.",
    fieldErrors: null,
    isNetworkError: false,
  };
}

function fallbackMessageForStatus(status: number): string {
  switch (status) {
    case 400:
      return "That request couldn't be processed.";
    case 401:
      return "You need to sign in to continue.";
    case 403:
      return "You don't have permission to do that.";
    case 404:
      return "We couldn't find what you were looking for.";
    case 409:
      return "This conflicts with something that already exists.";
    case 422:
      return "Please check the highlighted fields.";
    case 423:
      return "This account is temporarily locked.";
    case 429:
      return "Too many requests — please slow down and try again shortly.";
    case 500:
    case 502:
    case 503:
    case 504:
      return "Something went wrong on our end. Please try again in a moment.";
    default:
      return "Something went wrong. Please try again.";
  }
}

/** Field errors from the backend keyed by RHF field name, with `error_code` stripped out. */
export function extractFieldErrors(error: unknown): Record<string, string[]> {
  const normalized = normalizeApiError(error);
  if (!normalized.fieldErrors) return {};
  return Object.fromEntries(
    Object.entries(normalized.fieldErrors).filter(([field]) => field !== "error_code"),
  );
}
