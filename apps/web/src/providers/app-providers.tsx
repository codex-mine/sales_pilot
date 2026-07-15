"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useEffect, useState, type ReactNode } from "react";
import { getCurrentUser } from "@/features/auth/api/login";
import { useAuthStore } from "@/store/auth-store";

function AuthBootstrap() {
  const hydrateFromStorage = useAuthStore((state) => state.hydrateFromStorage);

  useEffect(() => {
    const restoreSession = async () => {
      hydrateFromStorage();

      const { accessToken, clearAuth } = useAuthStore.getState();
      if (!accessToken) return;

      try {
        const profileResponse = await getCurrentUser();

        console.log("Profile Response:", profileResponse);

        if (profileResponse.success && profileResponse.data) {
          useAuthStore.setState({
            user: {
              id: profileResponse.data.id,
              email: profileResponse.data.email,
              fullName: profileResponse.data.full_name,
              role: "member",
              organizationId: null,
              isVerified: profileResponse.data.is_verified,
            },
            isAuthenticated: true,
            isHydrated: true,
          });
          return;
        }
      } catch {
        clearAuth();
      }
    };

    void restoreSession();
  }, [hydrateFromStorage]);

  return null;
}

export function AppProviders({ children }: { children: ReactNode }): React.ReactElement {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30_000 } } }));

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={client}>
        <AuthBootstrap />
        {children}
      </QueryClientProvider>
    </ThemeProvider>
  );
}
