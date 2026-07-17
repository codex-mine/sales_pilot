"use client";

import { formatDistanceToNow } from "date-fns";
import { useState } from "react";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Link2, Search, Users } from "@/icons";
import { getInitials } from "@/lib/utils";
import { useCompanyEmployees } from "../hooks/use-company-employees";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

export interface CompanyEmployeesTableProps {
  companyId: string;
}

/** Read-only view over Contact rows linked to this company. Full employee management (invite, edit, deactivate) is deferred to a future Contacts module — this tab only displays. */
export function CompanyEmployeesTable({ companyId }: CompanyEmployeesTableProps): React.ReactElement {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 350);
  const [status, setStatus] = useState<string>("");
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const { employees, meta, isLoading } = useCompanyEmployees(companyId, {
    search: debouncedSearch || undefined,
    status: status || undefined,
    page,
    page_size: pageSize,
  });

  const pageCount = Math.max(Math.ceil(meta.total / meta.page_size), 1);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-64">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-8"
            placeholder="Search employees..."
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          value={status || "all"}
          onValueChange={(value) => {
            setStatus(value === "all" ? "" : value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : employees.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No employees yet"
          description="Contacts linked to this company will show up here."
        />
      ) : (
        <div className="overflow-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Job title</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Linked lead</TableHead>
                <TableHead>Last activity</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {employees.map((employee) => (
                <TableRow key={employee.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Avatar size="sm" fallback={getInitials(employee.full_name)} />
                      <span className="truncate text-body-sm font-medium text-foreground">{employee.full_name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-body-sm text-foreground">{employee.job_title || "—"}</TableCell>
                  <TableCell className="text-body-sm text-foreground">{employee.department || "—"}</TableCell>
                  <TableCell className="text-body-sm text-foreground">{employee.email}</TableCell>
                  <TableCell className="text-body-sm text-foreground">{employee.phone || "—"}</TableCell>
                  <TableCell>
                    <StatusBadge tone={employee.status === "active" ? "success" : "neutral"}>
                      {employee.status === "active" ? "Active" : "Inactive"}
                    </StatusBadge>
                  </TableCell>
                  <TableCell>
                    {employee.has_linked_lead ? (
                      <Badge variant="soft">
                        <Link2 className="size-3" />
                        Linked
                      </Badge>
                    ) : (
                      <span className="text-body-sm text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-body-sm text-muted-foreground">
                    {formatDistanceToNow(new Date(employee.last_activity_at), { addSuffix: true })}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {meta.total > pageSize && (
        <div className="flex items-center justify-between">
          <p className="text-body-sm text-muted-foreground">{meta.total} employee(s) total.</p>
          <Pagination page={meta.page} pageCount={pageCount} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}
