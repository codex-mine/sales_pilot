import logoMark from "@/logo.png";
import { cn } from "@/lib/utils";

const SIZES = {
  sm: { mark: 22, text: "text-body-md" },
  md: { mark: 28, text: "text-heading-6" },
  lg: { mark: 40, text: "text-heading-4" },
} as const;

export interface LogoProps {
  size?: keyof typeof SIZES;
  showWordmark?: boolean;
  className?: string;
}

/** The SalesPilot AI brand mark (`src/logo.png`) with an optional wordmark. Use everywhere branding appears — sidebar, auth pages, header. */
export function Logo({ size = "md", showWordmark = true, className }: LogoProps): React.ReactElement {
  const { mark, text } = SIZES[size];

  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      {/* eslint-disable-next-line @next/next/no-img-element -- statically imported local asset; no benefit from next/image's runtime optimizer here */}
      <img
        src={logoMark.src}
        alt={showWordmark ? "" : "SalesPilot AI"}
        width={mark}
        height={mark}
        className="shrink-0"
      />
      {showWordmark && (
        <span className={cn("font-display font-semibold text-foreground", text)}>SalesPilot AI</span>
      )}
    </span>
  );
}
