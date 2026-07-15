"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-16">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          404
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-slate-900">
          Page not found
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          The page you are looking for does not exist or may have been moved.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link href="/">
            <Button>Go home</Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="outline">Go to dashboard</Button>
          </Link>
        </div>
      </div>
    </main>
  );
}
