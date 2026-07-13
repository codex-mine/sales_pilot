"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
const schema = z.object({ email: z.string().email(), password: z.string().min(1) });
type FormData = z.infer<typeof schema>;
export default function LoginPage(): React.ReactElement { const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema) }); return <main className="mx-auto flex min-h-screen max-w-sm items-center p-6"><form className="w-full rounded-xl border bg-white p-6 shadow-sm" onSubmit={handleSubmit(() => undefined)}><h1 className="text-2xl font-semibold">Welcome back</h1><p className="mt-1 text-sm text-slate-500">Sign in to your workspace.</p><label className="mt-6 block text-sm font-medium">Email<input className="mt-1 w-full rounded-md border p-2" type="email" {...register("email")} /></label>{errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}<label className="mt-4 block text-sm font-medium">Password<input className="mt-1 w-full rounded-md border p-2" type="password" {...register("password")} /></label><Button className="mt-6 w-full" type="submit">Sign in</Button></form></main>; }
