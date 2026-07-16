import { Spinner } from "@/components/ui/spinner";

/** Shown while auth initialization is in flight — guards must never flash protected/guest content before this settles. */
export function AuthLoadingScreen(): React.ReactElement {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Spinner size="lg" label="Loading your workspace" />
    </div>
  );
}
