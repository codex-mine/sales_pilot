import Link from "next/link";
import { Button } from "@/components/ui/button";
export default function Home(): React.ReactElement {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center p-8">
      <p className="mb-4 text-sm font-semibold text-indigo-600">SALES PILOT</p>
      <h1 className="max-w-3xl text-5xl font-bold tracking-tight">
        A solid foundation for your future sales engine.
      </h1>
      <p className="mt-6 max-w-xl text-lg text-slate-600">
        The Phase 1 application shell is ready for teams, secure access, and
        future AI capabilities.
      </p>
      <Link className="mt-8" href="/dashboard">
        <Button>Open dashboard</Button>
      </Link>
    </main>
  );
}
