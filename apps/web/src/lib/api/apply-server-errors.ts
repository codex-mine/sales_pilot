import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { extractFieldErrors, normalizeApiError } from "./errors";

/**
 * Bridges a 422 validation response onto the right React Hook Form fields
 * (matching the backend's `errors` dict keys to form field names) and
 * returns whatever's left as a single banner message — either a non-field
 * error (401/403/409/423/429/500) or a fallback when nothing matched a
 * known field.
 */
export function applyServerErrors<TFieldValues extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<TFieldValues>,
): string | null {
  const normalized = normalizeApiError(error);
  const fieldErrors = extractFieldErrors(error);
  const fieldNames = Object.keys(fieldErrors);

  if (fieldNames.length === 0) {
    return normalized.message;
  }

  for (const field of fieldNames) {
    const messages = fieldErrors[field];
    if (messages?.length) {
      setError(field as Path<TFieldValues>, { type: "server", message: messages[0] });
    }
  }

  return null;
}
