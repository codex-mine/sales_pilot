"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FileUpload } from "@/components/ui/file-upload";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { StepIndicator } from "@/components/ui/step-indicator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AlertTriangle, CheckCircle2, FileSpreadsheet, XCircle } from "@/icons";
import { useImportLeads } from "../hooks/use-lead-import-export";
import type { ImportPreviewResponse, ImportResultResponse } from "../types";

const STEPS = [
  { label: "Upload", description: "Choose a CSV file" },
  { label: "Map fields", description: "Match columns to lead fields" },
  { label: "Summary", description: "Review results" },
];

const NONE_VALUE = "__none__";

export function LeadImportWizard(): React.ReactElement {
  const router = useRouter();
  const { previewImport, isPreviewing, commitImport, isCommitting } = useImportLeads();

  const [step, setStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ImportResultResponse | null>(null);

  async function handleFilesAdded(files: File[]): Promise<void> {
    const selected = files[0];
    if (!selected) return;
    setFile(selected);
    const previewResponse = await previewImport(selected);
    setPreview(previewResponse);
    setMapping(previewResponse.suggested_mapping);
    setStep(1);
  }

  async function handleCommit(): Promise<void> {
    if (!file) return;
    const activeMapping = Object.fromEntries(Object.entries(mapping).filter(([, field]) => field !== NONE_VALUE));
    const importResult = await commitImport({ file, mapping: activeMapping });
    setResult(importResult);
    setStep(2);
  }

  function reset(): void {
    setStep(0);
    setFile(null);
    setPreview(null);
    setMapping({});
    setResult(null);
  }

  return (
    <div className="flex flex-col gap-8">
      <StepIndicator steps={STEPS} currentStep={step} />

      {step === 0 && (
        <Card>
          <CardContent className="pt-6">
            <FileUpload
              onFilesAdded={handleFilesAdded}
              accept=".csv,text/csv"
              multiple={false}
              disabled={isPreviewing}
              label={isPreviewing ? "Analyzing your file..." : "Drag and drop a CSV file here"}
              hint="or click to browse. We'll auto-detect the columns."
            />
            <div className="mt-4 flex items-center gap-2 text-body-sm text-muted-foreground">
              <FileSpreadsheet className="size-4" />
              Need a starting point?{" "}
              <button type="button" className="text-primary hover:underline" onClick={downloadTemplate}>
                Download the CSV template
              </button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 1 && preview && (
        <div className="flex flex-col gap-4">
          <Card>
            <CardContent className="pt-6">
              <p className="mb-4 text-body-sm text-muted-foreground">
                {preview.total_rows} row{preview.total_rows === 1 ? "" : "s"} detected. Map each column to a lead
                field, or leave it unmapped to skip it.
              </p>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>CSV column</TableHead>
                      <TableHead>Maps to</TableHead>
                      <TableHead>Sample value</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preview.headers.map((header) => (
                      <TableRow key={header}>
                        <TableCell className="font-medium">{header}</TableCell>
                        <TableCell>
                          <Select
                            value={mapping[header] ?? NONE_VALUE}
                            onValueChange={(value) => setMapping((prev) => ({ ...prev, [header]: value }))}
                          >
                            <SelectTrigger className="w-48">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value={NONE_VALUE}>Don&apos;t import</SelectItem>
                              {preview.available_fields.map((field) => (
                                <SelectItem key={field} value={field}>
                                  {field.replace(/_/g, " ")}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell className="max-w-48 truncate text-body-sm text-muted-foreground">
                          {preview.sample_rows[0]?.[header] || "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
          <div className="flex justify-between">
            <Button variant="outline" onClick={reset}>
              Start over
            </Button>
            <Button onClick={handleCommit} isLoading={isCommitting}>
              Import {preview.total_rows} lead{preview.total_rows === 1 ? "" : "s"}
            </Button>
          </div>
        </div>
      )}

      {step === 2 && result && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <SummaryStat icon={CheckCircle2} tone="success" label="Imported" value={result.successful_count} />
            <SummaryStat icon={AlertTriangle} tone="warning" label="Duplicates skipped" value={result.duplicate_count} />
            <SummaryStat icon={XCircle} tone="danger" label="Failed" value={result.failed_count} />
          </div>

          {result.failed_rows.length > 0 && (
            <Card>
              <CardContent className="pt-6">
                <p className="mb-3 text-body-sm font-medium text-foreground">Failed rows</p>
                <div className="max-h-64 overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Row</TableHead>
                        <TableHead>Errors</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.failed_rows.map((row) => (
                        <TableRow key={row.row_number}>
                          <TableCell>{row.row_number}</TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {row.errors.map((error, i) => (
                                <Badge key={i} variant="danger">
                                  {error}
                                </Badge>
                              ))}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}

          {result.successful_count === 0 && result.failed_count === 0 && result.duplicate_count === 0 && (
            <Alert variant="info" icon={AlertTriangle}>
              <AlertDescription>The file had no importable rows.</AlertDescription>
            </Alert>
          )}

          <div className="flex justify-between">
            <Button variant="outline" onClick={reset}>
              Import another file
            </Button>
            <Button onClick={() => router.push("/leads")}>View leads</Button>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryStat({
  icon: Icon,
  tone,
  label,
  value,
}: {
  icon: typeof CheckCircle2;
  tone: "success" | "warning" | "danger";
  label: string;
  value: number;
}): React.ReactElement {
  const toneClass = { success: "text-success", warning: "text-warning", danger: "text-danger" }[tone];
  return (
    <Card>
      <CardContent className="flex items-center gap-3 pt-6">
        <Icon className={`size-8 ${toneClass}`} />
        <div className="flex flex-col">
          <span className="text-heading-4 font-semibold text-foreground">{value}</span>
          <span className="text-body-sm text-muted-foreground">{label}</span>
        </div>
      </CardContent>
    </Card>
  );
}

const TEMPLATE_HEADERS = [
  "First Name", "Last Name", "Email", "Phone", "Job Title", "Company", "Website",
  "Industry", "Status", "Source", "Country", "State", "City", "LinkedIn URL",
  "Tags",
];

function downloadTemplate(): void {
  const csv = `${TEMPLATE_HEADERS.join(",")}\n`;
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "leads-template.csv";
  link.click();
  URL.revokeObjectURL(url);
}
