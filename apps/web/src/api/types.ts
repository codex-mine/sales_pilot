export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  message: string;
  errors: Record<string, string[]> | null;
  meta: Record<string, unknown> | null;
}
