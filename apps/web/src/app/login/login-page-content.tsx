"use client";

import Link from "next/link";
import { GuestGuard } from "@/components/guards";
import { CenteredLayout } from "@/components/layout/centered-layout";
import { AuthCard } from "@/features/auth/components/auth-card";
import { LoginForm } from "@/features/auth/components/login-form";

export function LoginPageContent(): React.ReactElement {
  return (
    <GuestGuard>
      <CenteredLayout maxWidthClassName="max-w-sm">
        <AuthCard
          title="Welcome back"
          description="Sign in to your workspace."
          footer={
            <>
              Don&apos;t have a workspace?{" "}
              <Link href="/register" className="font-medium text-primary hover:underline">
                Create one
              </Link>
            </>
          }
        >
          <LoginForm />
        </AuthCard>
      </CenteredLayout>
    </GuestGuard>
  );
}
