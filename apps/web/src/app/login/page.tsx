"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { getCurrentUser, login } from "@/features/auth/api/login";
import { useAuthStore } from "@/store/auth-store";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage(): React.ReactElement {
  const router = useRouter();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setSubmitError(null);

    try {
      const response = await login({
        email: data.email,
        password: data.password,
      });

      if (response.success && response.data?.access_token) {
        const accessToken = response.data.access_token;
        const previousToken = useAuthStore.getState().accessToken;

        useAuthStore.setState({ accessToken, isAuthenticated: true });

        try {
          const profileResponse = await getCurrentUser();

          if (profileResponse.success && profileResponse.data) {
            setAuth({
              accessToken,
              user: {
                id: profileResponse.data.id,
                email: profileResponse.data.email,
                fullName: profileResponse.data.full_name,
                role: "member",
                organizationId: null,
                isVerified: profileResponse.data.is_verified,
              },
            });
            router.replace("/dashboard");
            return;
          }
        } catch (error) {
          useAuthStore.setState({
            accessToken: previousToken,
            isAuthenticated: Boolean(previousToken),
          });
          throw error;
        }
      }

      setSubmitError(response.message || "Invalid email or password");
    } catch (error: unknown) {
      const message =
        error && typeof error === "object" && "response" in error
          ? (error as { response?: { data?: { message?: string } } }).response
              ?.data?.message
          : undefined;

      setSubmitError(message || "Unable to sign in right now");
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-sm items-center p-6">
      <form
        className="w-full rounded-xl border bg-white p-6 shadow-sm"
        onSubmit={handleSubmit(onSubmit)}
      >
        <h1 className="text-2xl font-semibold">Welcome back</h1>
        <p className="mt-1 text-sm text-slate-500">
          Sign in to your workspace.
        </p>

        <label className="mt-6 block text-sm font-medium">
          Email
          <input
            className="mt-1 w-full rounded-md border p-2"
            type="email"
            {...register("email")}
          />
        </label>
        {errors.email && (
          <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
        )}

        <label className="mt-4 block text-sm font-medium">
          Password
          <input
            className="mt-1 w-full rounded-md border p-2"
            type="password"
            {...register("password")}
          />
        </label>
        {errors.password && (
          <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
        )}

        {submitError && (
          <p className="mt-3 text-sm text-red-600">{submitError}</p>
        )}

        <Button className="mt-6 w-full" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Sign in"}
        </Button>
      </form>
    </main>
  );
}
