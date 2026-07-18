"use client";

import { useState } from "react";
import { DataTable } from "@/components/data-table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAIJobs } from "../hooks/use-ai-jobs";
import { AI_JOB_STATUS_CHOICES, type AIJobStatus, type AIJobsQuery } from "../types";
import { aiJobsTableColumns } from "./ai-jobs-table-columns";
import { AIJobDetailDrawer } from "./ai-job-detail-drawer";

/** AI Job History: filterable table of every AIJob for the organization, row-click opens the full detail drawer. */
export function AIJobsTable(): React.ReactElement {
  const [query, setQuery] = useState<AIJobsQuery>({ page: 1, page_size: 25 });
  const [selectedJobId, setSelectedJobId] = useState<string | undefined>(undefined);

  const { jobs, isLoading } = useAIJobs(query);

  return (
    <>
      <DataTable
        columns={aiJobsTableColumns}
        data={jobs}
        isLoading={isLoading}
        searchPlaceholder="Search job type or entity..."
        emptyTitle="No AI jobs yet"
        emptyDescription="Every AI call the system makes — research, email generation, and more — will show up here."
        onRowClick={(job) => setSelectedJobId(job.id)}
        filters={
          <Select
            value={query.status?.[0] ?? "all"}
            onValueChange={(value) =>
              setQuery((prev) => ({ ...prev, status: value === "all" ? undefined : [value as AIJobStatus] }))
            }
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {AI_JOB_STATUS_CHOICES.map((status) => (
                <SelectItem key={status} value={status}>
                  {status}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      />
      <AIJobDetailDrawer jobId={selectedJobId} onOpenChange={(open) => !open && setSelectedJobId(undefined)} />
    </>
  );
}
