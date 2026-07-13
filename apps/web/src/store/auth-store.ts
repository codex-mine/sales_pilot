import { create } from "zustand";
import type { AuthUser } from "@/types/api";
interface AuthState { user: AuthUser | null; isAuthenticated: boolean; setUser: (user: AuthUser | null) => void; }
export const useAuthStore = create<AuthState>((set) => ({ user: null, isAuthenticated: false, setUser: (user) => set({ user, isAuthenticated: user !== null }) }));
