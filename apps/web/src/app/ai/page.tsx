import { AICostWidget } from "@/features/ai/components/ai-cost-widget";
import { AIJobsTable } from "@/features/ai/components/ai-jobs-table";

export default function AIJobsPage(): React.ReactElement {
  return (
    <div className="flex flex-col gap-6">
      <AICostWidget />
      <AIJobsTable />
    </div>
  );
}
