import { type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>): React.ReactElement { return <section className={cn("rounded-xl border bg-white p-5 shadow-sm dark:bg-slate-900", className)} {...props} />; }
