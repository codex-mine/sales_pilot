import { cva, type VariantProps } from "class-variance-authority";
import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";
const variants = cva("inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50", { variants: { variant: { default: "bg-indigo-600 text-white hover:bg-indigo-700", outline: "border bg-transparent hover:bg-slate-100 dark:hover:bg-slate-900", ghost: "hover:bg-slate-100 dark:hover:bg-slate-900" }, size: { default: "h-10 px-4 py-2", sm: "h-9 px-3", icon: "h-10 w-10" } }, defaultVariants: { variant: "default", size: "default" } });
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof variants> {}
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, ...props }, ref) => <button ref={ref} className={cn(variants({ variant, size }), className)} {...props} />);
Button.displayName = "Button";
