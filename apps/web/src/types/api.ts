export interface ApiResponse<T> { success: boolean; data: T | null; message: string; errors: Record<string, string[]> | null; meta: Record<string, unknown> | null; }
export type UserRole = "owner" | "admin" | "member";
export interface AuthUser { id: string; email: string; fullName: string | null; role: UserRole; organizationId: string | null; isVerified?: boolean; }
