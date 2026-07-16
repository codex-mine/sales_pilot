import type { Config } from "tailwindcss";
import animatePlugin from "tailwindcss-animate";

/**
 * Tailwind theme configuration for the SalesPilot design system.
 *
 * Every color, radius, shadow, and motion value here is a CSS custom
 * property defined in `src/styles/globals.css` — nothing is a literal
 * hex/rgb value. This file only *maps* token names to those variables so
 * components can write `bg-primary`, `rounded-lg`, `shadow-dropdown`, etc.
 * and automatically get correct light/dark values with zero conditional
 * logic in component code.
 *
 * Colors use the `<h> <s> <l>` (space-separated, unitless) convention so
 * Tailwind's opacity modifiers work: `bg-primary/10`, `ring-ring/50`, etc.
 * compile to `hsl(var(--primary) / 0.1)`.
 */
const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx,mdx}"],
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: "1rem",
        sm: "1.5rem",
        lg: "2rem",
      },
      screens: {
        sm: "640px",
        md: "768px",
        lg: "1024px",
        xl: "1280px",
        "2xl": "1440px",
      },
    },
    extend: {
      // ─── Spacing tokens ──────────────────────────────────────────────────
      // A fixed, named px-based scale layered on top of Tailwind's default
      // rem scale. Prefer these values (2/4/6/8/10/12/16/20/24/32/40/48/56/
      // 64/80/96/128) for anything intentional — layout gaps, paddings,
      // component sizing. The rest of Tailwind's default scale remains
      // available as an escape hatch, but code review should question any
      // spacing value that isn't in this list.
      spacing: {
        "0.5": "0.125rem", // 2px
        "1": "0.25rem", // 4px
        "1.5": "0.375rem", // 6px
        "2": "0.5rem", // 8px
        "2.5": "0.625rem", // 10px
        "3": "0.75rem", // 12px
        "4": "1rem", // 16px
        "5": "1.25rem", // 20px
        "6": "1.5rem", // 24px
        "8": "2rem", // 32px
        "10": "2.5rem", // 40px
        "12": "3rem", // 48px
        "14": "3.5rem", // 56px
        "16": "4rem", // 64px
        "20": "5rem", // 80px
        "24": "6rem", // 96px
        "32": "8rem", // 128px
      },

      // ─── Radius tokens ───────────────────────────────────────────────────
      borderRadius: {
        xs: "var(--radius-xs)",
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
        "2xl": "var(--radius-2xl)",
        full: "var(--radius-full)",
      },

      // ─── Color tokens ────────────────────────────────────────────────────
      colors: {
        border: "hsl(var(--border) / <alpha-value>)",
        input: "hsl(var(--input) / <alpha-value>)",
        ring: "hsl(var(--ring) / <alpha-value>)",
        background: "hsl(var(--background) / <alpha-value>)",
        foreground: "hsl(var(--foreground) / <alpha-value>)",
        overlay: "hsl(var(--overlay) / <alpha-value>)",

        primary: {
          DEFAULT: "hsl(var(--primary) / <alpha-value>)",
          hover: "hsl(var(--primary-hover) / <alpha-value>)",
          foreground: "hsl(var(--primary-foreground) / <alpha-value>)",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary) / <alpha-value>)",
          foreground: "hsl(var(--secondary-foreground) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "hsl(var(--accent) / <alpha-value>)",
          foreground: "hsl(var(--accent-foreground) / <alpha-value>)",
        },
        muted: {
          DEFAULT: "hsl(var(--muted) / <alpha-value>)",
          foreground: "hsl(var(--muted-foreground) / <alpha-value>)",
        },
        card: {
          DEFAULT: "hsl(var(--card) / <alpha-value>)",
          foreground: "hsl(var(--card-foreground) / <alpha-value>)",
        },
        popover: {
          DEFAULT: "hsl(var(--popover) / <alpha-value>)",
          foreground: "hsl(var(--popover-foreground) / <alpha-value>)",
        },

        success: {
          DEFAULT: "hsl(var(--success) / <alpha-value>)",
          foreground: "hsl(var(--success-foreground) / <alpha-value>)",
          soft: "hsl(var(--success-soft) / <alpha-value>)",
        },
        warning: {
          DEFAULT: "hsl(var(--warning) / <alpha-value>)",
          foreground: "hsl(var(--warning-foreground) / <alpha-value>)",
          soft: "hsl(var(--warning-soft) / <alpha-value>)",
        },
        danger: {
          DEFAULT: "hsl(var(--danger) / <alpha-value>)",
          foreground: "hsl(var(--danger-foreground) / <alpha-value>)",
          soft: "hsl(var(--danger-soft) / <alpha-value>)",
        },
        // `destructive` alias kept for shadcn/ui component parity.
        destructive: {
          DEFAULT: "hsl(var(--danger) / <alpha-value>)",
          foreground: "hsl(var(--danger-foreground) / <alpha-value>)",
        },
        info: {
          DEFAULT: "hsl(var(--info) / <alpha-value>)",
          foreground: "hsl(var(--info-foreground) / <alpha-value>)",
          soft: "hsl(var(--info-soft) / <alpha-value>)",
        },

        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background) / <alpha-value>)",
          foreground: "hsl(var(--sidebar-foreground) / <alpha-value>)",
          primary: "hsl(var(--sidebar-primary) / <alpha-value>)",
          "primary-foreground":
            "hsl(var(--sidebar-primary-foreground) / <alpha-value>)",
          accent: "hsl(var(--sidebar-accent) / <alpha-value>)",
          "accent-foreground":
            "hsl(var(--sidebar-accent-foreground) / <alpha-value>)",
          border: "hsl(var(--sidebar-border) / <alpha-value>)",
          ring: "hsl(var(--sidebar-ring) / <alpha-value>)",
        },

        skeleton: "hsl(var(--skeleton) / <alpha-value>)",

        chart: {
          "1": "hsl(var(--chart-1) / <alpha-value>)",
          "2": "hsl(var(--chart-2) / <alpha-value>)",
          "3": "hsl(var(--chart-3) / <alpha-value>)",
          "4": "hsl(var(--chart-4) / <alpha-value>)",
          "5": "hsl(var(--chart-5) / <alpha-value>)",
        },
      },

      // ─── Typography tokens ───────────────────────────────────────────────
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        // Body / UI scale
        caption: ["0.75rem", { lineHeight: "1rem", letterSpacing: "0" }],
        "body-sm": ["0.8125rem", { lineHeight: "1.25rem", letterSpacing: "0" }],
        "body-md": ["0.875rem", { lineHeight: "1.375rem", letterSpacing: "0" }],
        "body-lg": ["1rem", { lineHeight: "1.5rem", letterSpacing: "0" }],
        "body-xl": ["1.125rem", { lineHeight: "1.75rem", letterSpacing: "0" }],
        overline: [
          "0.6875rem",
          { lineHeight: "1rem", letterSpacing: "0.08em" },
        ],
        // Heading scale
        "heading-6": ["1rem", { lineHeight: "1.5rem", letterSpacing: "-0.01em" }],
        "heading-5": ["1.125rem", { lineHeight: "1.625rem", letterSpacing: "-0.01em" }],
        "heading-4": ["1.25rem", { lineHeight: "1.75rem", letterSpacing: "-0.015em" }],
        "heading-3": ["1.5rem", { lineHeight: "2rem", letterSpacing: "-0.015em" }],
        "heading-2": ["1.875rem", { lineHeight: "2.375rem", letterSpacing: "-0.02em" }],
        "heading-1": ["2.25rem", { lineHeight: "2.75rem", letterSpacing: "-0.02em" }],
        // Display scale (Poppins, marketing/landing use only)
        "display-sm": ["2.5rem", { lineHeight: "3rem", letterSpacing: "-0.02em" }],
        "display-md": ["3rem", { lineHeight: "3.5rem", letterSpacing: "-0.025em" }],
        "display-lg": ["3.75rem", { lineHeight: "4.25rem", letterSpacing: "-0.025em" }],
        "display-xl": ["4.5rem", { lineHeight: "5rem", letterSpacing: "-0.03em" }],
      },

      // ─── Shadow tokens ───────────────────────────────────────────────────
      boxShadow: {
        sm: "var(--shadow-sm)",
        DEFAULT: "var(--shadow-md)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        dropdown: "var(--shadow-dropdown)",
        floating: "var(--shadow-floating)",
        modal: "var(--shadow-modal)",
        popover: "var(--shadow-popover)",
        sidebar: "var(--shadow-sidebar)",
      },

      // ─── Motion tokens ───────────────────────────────────────────────────
      transitionDuration: {
        fast: "var(--duration-fast)",
        normal: "var(--duration-normal)",
        slow: "var(--duration-slow)",
      },
      transitionTimingFunction: {
        standard: "var(--ease-standard)",
        emphasized: "var(--ease-emphasized)",
        decelerate: "var(--ease-decelerate)",
        accelerate: "var(--ease-accelerate)",
      },

      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "collapsible-down": {
          from: { height: "0" },
          to: { height: "var(--radix-collapsible-content-height)" },
        },
        "collapsible-up": {
          from: { height: "var(--radix-collapsible-content-height)" },
          to: { height: "0" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "spin-slow": {
          to: { transform: "rotate(360deg)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down var(--duration-normal) var(--ease-standard)",
        "accordion-up": "accordion-up var(--duration-normal) var(--ease-standard)",
        "collapsible-down": "collapsible-down var(--duration-normal) var(--ease-standard)",
        "collapsible-up": "collapsible-up var(--duration-normal) var(--ease-standard)",
        shimmer: "shimmer 2s infinite",
        "spin-slow": "spin-slow 1.2s linear infinite",
      },
    },
  },
  plugins: [animatePlugin],
};

export default config;
