"use client";

import { useRef, useState } from "react";

import { parseCandidateCsvFile, type CsvParseResult, type CsvValidationIssue } from "@/lib/csv";

export interface CsvSelection {
  file: File;
  result: CsvParseResult;
}

export function CsvValidationMessages({ issues }: { issues: CsvValidationIssue[] }) {
  if (issues.length === 0) return null;
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4">
      <p className="text-sm font-bold text-red-950">Validation needs attention</p>
      <ul className="mt-2 space-y-1 text-sm text-red-800">
        {issues.slice(0, 8).map((issue, index) => (
          <li key={`${issue.code}-${issue.row_number}-${issue.field}-${index}`}>
            {issue.row_number ? `Row ${issue.row_number}: ` : ""}{issue.message}
          </li>
        ))}
      </ul>
      {issues.length > 8 ? <p className="mt-2 text-xs font-semibold text-red-700">+ {issues.length - 8} more issues</p> : null}
    </div>
  );
}

export function CsvUpload({ selection, onChange }: { selection: CsvSelection | null; onChange: (value: CsvSelection | null) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [reading, setReading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  const processFile = async (file: File | undefined) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv") && file.type !== "text/csv") {
      setFileError("Choose a CSV file with a .csv extension.");
      return;
    }
    setReading(true);
    setFileError(null);
    try {
      onChange({ file, result: await parseCandidateCsvFile(file) });
    } catch {
      setFileError("This file could not be read. Replace it with a valid UTF-8 CSV.");
    } finally {
      setReading(false);
    }
  };

  if (selection) {
    const { file, result } = selection;
    return (
      <div className="space-y-4">
        <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-ink">{file.name}</p>
            <p className="mt-1 text-xs text-slate-500">{formatBytes(file.size)} · {result.rows.length} parsed rows</p>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => inputRef.current?.click()} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-100">Replace file</button>
            <button type="button" onClick={() => onChange(null)} className="rounded-md px-3 py-2 text-xs font-bold text-red-700 hover:bg-red-50">Remove</button>
          </div>
        </div>
        <input ref={inputRef} type="file" accept=".csv,text/csv" className="sr-only" aria-label="Replace candidate-site CSV" onChange={(event) => void processFile(event.target.files?.[0])} />

        <div aria-label="Upload summary" className="grid grid-cols-3 gap-2">
          <UploadMetric label="Valid" value={result.valid_count} tone="text-emerald-700" />
          <UploadMetric label="Invalid" value={result.invalid_count} tone="text-red-700" />
          <UploadMetric label="Duplicates" value={result.duplicate_count} tone="text-amber-700" />
        </div>

        <CsvValidationMessages issues={result.issues} />
        {result.rows.length > 0 ? <CsvPreview result={result} /> : null}
      </div>
    );
  }

  return (
    <div>
      <div
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => { event.preventDefault(); setDragging(false); }}
        onDrop={(event) => { event.preventDefault(); setDragging(false); void processFile(event.dataTransfer.files?.[0]); }}
        className={`rounded-xl border-2 border-dashed px-5 py-10 text-center transition-colors ${dragging ? "border-forest bg-mint/70" : "border-slate-300 bg-slate-50"}`}
      >
        <span className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-white text-xl text-forest shadow-sm" aria-hidden="true">↑</span>
        <p className="mt-4 text-sm font-bold text-ink">{reading ? "Reading CSV…" : "Drop a candidate-site CSV here"}</p>
        <p className="mt-1 text-xs text-slate-500">Required: site name, coordinates, acreage, and jurisdiction</p>
        <label className="mt-5 inline-flex cursor-pointer rounded-md bg-forest px-4 py-2.5 text-sm font-bold text-white hover:bg-[#123e39]">
          Select CSV file
          <input type="file" accept=".csv,text/csv" className="sr-only" aria-label="Select candidate-site CSV" disabled={reading} onChange={(event) => void processFile(event.target.files?.[0])} />
        </label>
      </div>
      {fileError ? <p role="alert" className="mt-3 text-sm font-semibold text-red-700">{fileError}</p> : null}
    </div>
  );
}

function UploadMetric({ label, value, tone }: { label: string; value: number; tone: string }) {
  return <div className="rounded-lg border border-slate-200 bg-white p-3 text-center"><p className={`font-mono text-xl font-bold ${tone}`}>{value}</p><p className="mt-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">{label}</p></div>;
}

function CsvPreview({ result }: { result: CsvParseResult }) {
  const visibleHeaders = result.headers.slice(0, 8);
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h3 className="text-sm font-bold text-ink">Parsed row preview</h3>
        <span className="text-xs text-slate-500">Showing {Math.min(result.rows.length, 5)} of {result.rows.length}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-[760px] w-full text-left text-xs">
          <thead className="bg-slate-50 text-[10px] uppercase tracking-wider text-slate-500">
            <tr><th className="px-3 py-2 font-bold">Row</th>{visibleHeaders.map((header) => <th key={header} className="px-3 py-2 font-bold">{header.replaceAll("_", " ")}</th>)}<th className="px-3 py-2 font-bold">Validation</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {result.rows.slice(0, 5).map((row) => (
              <tr key={row.row_number} className={row.issues.length > 0 ? "bg-red-50/50" : ""}>
                <td className="px-3 py-2 font-mono text-slate-500">{row.row_number}</td>
                {visibleHeaders.map((header) => <td key={header} className="max-w-40 truncate px-3 py-2 text-slate-700">{row.values[header] || "—"}</td>)}
                <td className="px-3 py-2"><span className={`font-bold ${row.issues.length > 0 ? "text-red-700" : "text-emerald-700"}`}>{row.issues.length > 0 ? `${row.issues.length} issue${row.issues.length === 1 ? "" : "s"}` : "Valid"}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}
