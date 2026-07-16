import { cn } from "@/lib/utils";

export interface CircularProgressProps {
  /** 0-100. Omit for an indeterminate spinner ring. */
  value?: number;
  size?: number;
  strokeWidth?: number;
  tone?: "primary" | "success" | "warning" | "danger" | "info";
  className?: string;
  showLabel?: boolean;
}

const toneClass: Record<NonNullable<CircularProgressProps["tone"]>, string> = {
  primary: "stroke-primary",
  success: "stroke-success",
  warning: "stroke-warning",
  danger: "stroke-danger",
  info: "stroke-info",
};

/** A circular progress ring — used for compact completion/score indicators (e.g. lead score, quota). */
export function CircularProgress({
  value,
  size = 48,
  strokeWidth = 4,
  tone = "primary",
  className,
  showLabel = false,
}: CircularProgressProps): React.ReactElement {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const isIndeterminate = value === undefined;
  const offset = isIndeterminate ? circumference * 0.25 : circumference - (value / 100) * circumference;

  return (
    <div
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: size, height: size }}
      role="progressbar"
      aria-valuenow={isIndeterminate ? undefined : value}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className={cn(isIndeterminate && "animate-spin-slow")}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          className="fill-none stroke-muted"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          className={cn("fill-none transition-[stroke-dashoffset] duration-slow ease-standard", toneClass[tone])}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      {showLabel && !isIndeterminate && (
        <span className="absolute text-caption font-semibold text-foreground">{Math.round(value)}%</span>
      )}
    </div>
  );
}
