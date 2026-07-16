import { Check } from "@/icons";
import { cn } from "@/lib/utils";

export interface Step {
  label: string;
  description?: string;
}

export interface StepIndicatorProps {
  steps: Step[];
  /** Zero-based index of the current step. */
  currentStep: number;
  orientation?: "horizontal" | "vertical";
  className?: string;
}

/** A numbered multi-step progress indicator (onboarding wizards, multi-step forms). */
export function StepIndicator({
  steps,
  currentStep,
  orientation = "horizontal",
  className,
}: StepIndicatorProps): React.ReactElement {
  return (
    <ol
      className={cn(
        "flex",
        orientation === "horizontal" ? "w-full items-start" : "flex-col gap-6",
        className,
      )}
    >
      {steps.map((step, index) => {
        const isComplete = index < currentStep;
        const isCurrent = index === currentStep;
        const isLast = index === steps.length - 1;

        return (
          <li
            key={step.label}
            className={cn(
              "flex",
              orientation === "horizontal" ? "flex-1 flex-col items-center gap-2 text-center" : "flex-row gap-3",
            )}
          >
            <div className={cn("flex items-center", orientation === "horizontal" ? "w-full" : "flex-col")}>
              {orientation === "vertical" && !isLast && (
                <span className="mt-1 h-full min-h-6 w-px flex-1 bg-border" aria-hidden="true" />
              )}
              <span
                className={cn(
                  "flex size-8 shrink-0 items-center justify-center rounded-full border text-body-sm font-medium",
                  isComplete && "border-primary bg-primary text-primary-foreground",
                  isCurrent && "border-primary text-primary",
                  !isComplete && !isCurrent && "border-border text-muted-foreground",
                )}
              >
                {isComplete ? <Check className="size-4" /> : index + 1}
              </span>
              {orientation === "horizontal" && !isLast && (
                <span className={cn("mx-2 h-px flex-1", isComplete ? "bg-primary" : "bg-border")} aria-hidden="true" />
              )}
            </div>
            <div className={cn("flex flex-col", orientation === "vertical" && "pb-6")}>
              <span className={cn("text-body-sm font-medium", isCurrent ? "text-foreground" : "text-muted-foreground")}>
                {step.label}
              </span>
              {step.description && (
                <span className="text-caption text-muted-foreground">{step.description}</span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
