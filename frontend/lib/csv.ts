import type { CandidateSiteInput } from "@/types/api";

export const REQUIRED_COLUMNS = [
  "site_name",
  "latitude",
  "longitude",
  "acreage",
  "jurisdiction",
] as const;

export const OPTIONAL_COLUMNS = [
  "road_distance_miles",
  "flood_overlap_percent",
  "wetland_overlap_percent",
] as const;

export type CsvIssueCode =
  | "missing_column"
  | "missing_value"
  | "invalid_number"
  | "out_of_range"
  | "duplicate_row"
  | "empty_file";

export interface CsvValidationIssue {
  code: CsvIssueCode;
  message: string;
  row_number: number | null;
  field: string | null;
}

export interface CsvPreviewRow {
  row_number: number;
  values: Record<string, string>;
  candidate: CandidateSiteInput | null;
  issues: CsvValidationIssue[];
}

export interface CsvParseResult {
  headers: string[];
  rows: CsvPreviewRow[];
  issues: CsvValidationIssue[];
  valid_count: number;
  invalid_count: number;
  duplicate_count: number;
}

function splitCsvLine(line: string): string[] {
  const cells: string[] = [];
  let cell = "";
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    if (character === '"') {
      if (quoted && line[index + 1] === '"') {
        cell += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (character === "," && !quoted) {
      cells.push(cell.trim());
      cell = "";
    } else {
      cell += character;
    }
  }

  cells.push(cell.trim());
  return cells;
}

function numberIssue(
  value: string,
  field: string,
  rowNumber: number,
  options: { min?: number; max?: number; exclusiveMin?: boolean } = {},
): CsvValidationIssue | null {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return {
      code: "invalid_number",
      message: `${field} must be a valid number`,
      row_number: rowNumber,
      field,
    };
  }

  const belowMinimum =
    options.min !== undefined &&
    (options.exclusiveMin ? parsed <= options.min : parsed < options.min);
  const aboveMaximum = options.max !== undefined && parsed > options.max;
  if (belowMinimum || aboveMaximum) {
    const range = options.max === undefined ? `greater than ${options.min}` : `${options.min} to ${options.max}`;
    return {
      code: "out_of_range",
      message: `${field} must be ${range}`,
      row_number: rowNumber,
      field,
    };
  }

  return null;
}

function optionalNumber(value: string | undefined): number | null {
  return value === undefined || value === "" ? null : Number(value);
}

export function parseCandidateCsv(text: string): CsvParseResult {
  const lines = text
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0);

  if (lines.length === 0) {
    const issue: CsvValidationIssue = {
      code: "empty_file",
      message: "The CSV file is empty",
      row_number: null,
      field: null,
    };
    return { headers: [], rows: [], issues: [issue], valid_count: 0, invalid_count: 0, duplicate_count: 0 };
  }

  const headers = splitCsvLine(lines[0]).map((header) => header.trim().toLowerCase());
  const issues: CsvValidationIssue[] = REQUIRED_COLUMNS.filter(
    (column) => !headers.includes(column),
  ).map((column) => ({
    code: "missing_column" as const,
    message: `Missing required column: ${column}`,
    row_number: null,
    field: column,
  }));

  const duplicateKeys = new Set<string>();
  const rows = lines.slice(1).map((line, lineIndex): CsvPreviewRow => {
    const rowNumber = lineIndex + 2;
    const cells = splitCsvLine(line);
    const values = Object.fromEntries(headers.map((header, index) => [header, cells[index] ?? ""]));
    const rowIssues: CsvValidationIssue[] = [];

    for (const field of REQUIRED_COLUMNS) {
      if (headers.includes(field) && !values[field]?.trim()) {
        rowIssues.push({
          code: "missing_value",
          message: `${field} is required`,
          row_number: rowNumber,
          field,
        });
      }
    }

    const numericChecks: Array<[
      string,
      { min?: number; max?: number; exclusiveMin?: boolean },
      boolean,
    ]> = [
      ["latitude", { min: -90, max: 90 }, true],
      ["longitude", { min: -180, max: 180 }, true],
      ["acreage", { min: 0, exclusiveMin: true }, true],
      ["road_distance_miles", { min: 0 }, false],
      ["flood_overlap_percent", { min: 0, max: 100 }, false],
      ["wetland_overlap_percent", { min: 0, max: 100 }, false],
    ];

    for (const [field, options, required] of numericChecks) {
      const value = values[field];
      if (!headers.includes(field) || (!required && !value)) continue;
      if (!value) continue;
      const issue = numberIssue(value, field, rowNumber, options);
      if (issue) rowIssues.push(issue);
    }

    if (values.site_name && values.latitude && values.longitude) {
      const duplicateKey = `${values.site_name.trim().toLowerCase()}|${values.latitude}|${values.longitude}`;
      if (duplicateKeys.has(duplicateKey)) {
        rowIssues.push({
          code: "duplicate_row",
          message: `Duplicate site: ${values.site_name}`,
          row_number: rowNumber,
          field: "site_name",
        });
      }
      duplicateKeys.add(duplicateKey);
    }

    const candidate =
      issues.length === 0 && rowIssues.length === 0
        ? {
            site_name: values.site_name,
            latitude: Number(values.latitude),
            longitude: Number(values.longitude),
            acreage: Number(values.acreage),
            jurisdiction: values.jurisdiction,
            road_distance_miles: optionalNumber(values.road_distance_miles),
            flood_overlap_percent: optionalNumber(values.flood_overlap_percent),
            wetland_overlap_percent: optionalNumber(values.wetland_overlap_percent),
          }
        : null;

    return { row_number: rowNumber, values, candidate, issues: rowIssues };
  });

  const rowIssues = rows.flatMap((row) => row.issues);
  return {
    headers,
    rows,
    issues: [...issues, ...rowIssues],
    valid_count: rows.filter((row) => row.candidate !== null).length,
    invalid_count: rows.filter((row) => row.candidate === null).length,
    duplicate_count: rowIssues.filter((issue) => issue.code === "duplicate_row").length,
  };
}

export async function parseCandidateCsvFile(file: File): Promise<CsvParseResult> {
  return parseCandidateCsv(await file.text());
}
