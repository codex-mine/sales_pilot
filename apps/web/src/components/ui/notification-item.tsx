import type { IconComponent } from "@/icons";
import { cn } from "@/lib/utils";
import { Avatar } from "./avatar";

export interface NotificationItemProps {
  title: string;
  description?: string;
  timestamp: string;
  isRead?: boolean;
  icon?: IconComponent;
  avatarSrc?: string;
  avatarFallback?: string;
  onClick?: () => void;
  className?: string;
}

/** A single row in a notification feed/dropdown — icon or avatar, message, timestamp, and an unread indicator. */
export function NotificationItem({
  title,
  description,
  timestamp,
  isRead = false,
  icon: Icon,
  avatarSrc,
  avatarFallback,
  onClick,
  className,
}: NotificationItemProps): React.ReactElement {
  const Comp = onClick ? "button" : "div";

  return (
    <Comp
      onClick={onClick}
      className={cn(
        "flex w-full gap-3 rounded-md p-3 text-left transition-colors duration-fast ease-standard",
        onClick && "cursor-pointer hover:bg-muted",
        !isRead && "bg-accent/40",
        className,
      )}
    >
      {Icon ? (
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground">
          <Icon className="size-4" />
        </span>
      ) : (
        <Avatar size="sm" src={avatarSrc} fallback={avatarFallback} />
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <p className="text-body-sm text-foreground">
          <span className="font-medium">{title}</span>
          {description && <span className="text-muted-foreground"> {description}</span>}
        </p>
        <span className="text-caption text-muted-foreground">{timestamp}</span>
      </div>
      {!isRead && <span className="mt-1.5 size-2 shrink-0 rounded-full bg-primary" aria-label="Unread" />}
    </Comp>
  );
}
