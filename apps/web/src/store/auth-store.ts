import { create } from "zustand";
import { authService } from "@/features/auth/services/auth.service";
import type {
  MeResponse,
  OrganizationResponse,
  SessionResponse,
  UserResponse,
} from "@/features/auth/types";
import { normalizeApiError } from "@/lib/api/errors";
import { registerSessionExpiredHandler, setInMemoryAccessToken } from "@/lib/api/client";

export type RefreshStatus = "idle" | "refreshing" | "error";

interface AuthState {
  // ─── State ──────────────────────────────────────────────────────────────
  user: UserResponse | null;
  organization: OrganizationResponse | null;
  workspace: OrganizationResponse | null;
  permissions: string[];
  roles: string[];
  isAuthenticated: boolean;
  /** True once the boot-time `initialize()` call has settled (success or failure). Gates the whole app's first render. */
  isInitialized: boolean;
  accessToken: string | null;
  refreshStatus: RefreshStatus;
  isLoading: boolean;
  error: string | null;
  currentSession: SessionResponse | null;
  /** Present for forward-compatibility with multi-org membership (see ARCHITECTURE.md's V2 notes) — today it always mirrors `organization.id`. */
  selectedOrganizationId: string | null;

  // ─── Actions ────────────────────────────────────────────────────────────
  initialize: () => Promise<void>;
  loadUser: () => Promise<void>;
  login: (payload: { email: string; password: string; remember_me: boolean }) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refresh: () => Promise<void>;
  setCurrentSession: (session: SessionResponse | null) => void;
  setSelectedOrganization: (organizationId: string) => void;
  clear: () => void;
}

function applyMeResponse(me: MeResponse) {
  return {
    user: me.user,
    organization: me.organization,
    workspace: me.workspace,
    permissions: me.permissions,
    roles: me.user.roles,
    isAuthenticated: true,
    selectedOrganizationId: me.organization.id,
  };
}

const initialState = {
  user: null,
  organization: null,
  workspace: null,
  permissions: [] as string[],
  roles: [] as string[],
  isAuthenticated: false,
  isInitialized: false,
  accessToken: null,
  refreshStatus: "idle" as RefreshStatus,
  isLoading: false,
  error: null,
  currentSession: null,
  selectedOrganizationId: null,
};

export const useAuthStore = create<AuthState>((set, get) => ({
  ...initialState,

  // Boot sequence (see AUTHENTICATION.md / Step 5): try to load the current
  // user from the existing httpOnly session cookies. A 401 here is handled
  // transparently by the API client's response interceptor, which attempts
  // exactly one refresh-and-retry before giving up — so by the time this
  // rejects, the session is genuinely gone, not just momentarily expired.
  initialize: async () => {
    set({ isLoading: true, error: null });
    try {
      await get().loadUser();
    } catch {
      set({ ...initialState, isInitialized: true, isLoading: false });
      return;
    }
    set({ isInitialized: true, isLoading: false });
  },

  // Fetches /auth/me and populates user + organization + workspace +
  // permissions + roles in one round trip. Used by both `initialize()` and
  // immediately after `login()` (the login response itself only carries the
  // user, not org/workspace/permissions).
  loadUser: async () => {
    const response = await authService.me();
    if (!response.data) throw new Error("No user data returned.");
    set(applyMeResponse(response.data));
  },

  login: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      await authService.login(payload);
      await get().loadUser();
      set({ isLoading: false });
    } catch (error) {
      const normalized = normalizeApiError(error);
      set({ isLoading: false, error: normalized.message });
      throw error;
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      await authService.logout();
    } finally {
      get().clear();
    }
  },

  logoutAll: async () => {
    set({ isLoading: true });
    try {
      await authService.logoutAll();
    } finally {
      get().clear();
    }
  },

  // Manual refresh trigger (e.g. a "keep session alive" ping). The API
  // client's interceptor already does this automatically on a 401 — this
  // exists for callers that want to refresh proactively.
  refresh: async () => {
    set({ refreshStatus: "refreshing" });
    try {
      const response = await authService.refresh();
      if (response.data?.access_token) {
        setInMemoryAccessToken(response.data.access_token);
        set({ accessToken: response.data.access_token, refreshStatus: "idle" });
      } else {
        set({ refreshStatus: "idle" });
      }
    } catch (error) {
      set({ refreshStatus: "error" });
      throw error;
    }
  },

  setCurrentSession: (session) => set({ currentSession: session }),
  setSelectedOrganization: (organizationId) => set({ selectedOrganizationId: organizationId }),

  clear: () => {
    setInMemoryAccessToken(null);
    set({ ...initialState, isInitialized: true, isLoading: false });
  },
}));

// Wired once at module load: when the API client exhausts its one refresh
// attempt on a 401, the session is unrecoverable — drop to signed-out state
// so guards redirect to /login instead of the app hanging in a broken
// "authenticated but every request 401s" limbo.
registerSessionExpiredHandler(() => useAuthStore.getState().clear());
