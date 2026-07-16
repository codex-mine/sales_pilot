import { AppShell } from "@/components/layouts/app-shell";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
const cards = ["Pipeline", "Engagement", "Team activity"];
export default function DashboardPage(): React.ReactElement {
  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Your workspace will come to life as you connect future sales
          workflows.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {cards.map((title) => (
          <Card key={title}>
            <p className="text-sm text-slate-500">{title}</p>
            <p className="mt-4 text-3xl font-semibold">—</p>
          </Card>
        ))}
      </div>
      <div className="mt-6">
        <EmptyState
          title="Your dashboard is ready"
          description="Campaigns, insights, and AI workflows will appear here when those features are introduced."
        />
      </div>
    </AppShell>
  );
}
