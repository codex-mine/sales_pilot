import { ShieldAlert } from "@/icons";
import { EmptyState } from "@/components/ui/empty-state";

export function AccessDenied({
  description = "You don't have permission to view this page. Contact your workspace admin if you think this is a mistake.",
}: {
  description?: string;
}): React.ReactElement {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <EmptyState icon={ShieldAlert} title="Access denied" description={description} />
    </div>
  );
}
