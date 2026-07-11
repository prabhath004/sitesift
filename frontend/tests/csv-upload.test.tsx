import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { CsvUpload } from "@/components/forms/csv-upload";
import { parseCandidateCsv } from "@/lib/csv";

const validCsv = `site_name,latitude,longitude,acreage,jurisdiction,road_distance_miles,flood_overlap_percent,wetland_overlap_percent
River Road,42.110,-73.910,34,Greenfield County,0.7,0,2`;

test("parses and previews a valid candidate CSV", () => {
  const result = parseCandidateCsv(validCsv);
  expect(result.valid_count).toBe(1);
  expect(result.issues).toHaveLength(0);

  render(<CsvUpload selection={{ file: new File([validCsv], "sites.csv", { type: "text/csv" }), result }} onChange={vi.fn()} />);
  expect(screen.getByText("Parsed row preview")).toBeInTheDocument();
  expect(screen.getByText("River Road")).toBeInTheDocument();
  expect(screen.getAllByText("Valid")).toHaveLength(2);
});

test("reports missing columns, invalid numbers, and duplicate rows", () => {
  const missing = parseCandidateCsv("site_name,latitude,acreage,jurisdiction\nBad Site,nope,0,County");
  expect(missing.issues.map((issue) => issue.code)).toContain("missing_column");
  expect(missing.issues.map((issue) => issue.code)).toContain("invalid_number");
  expect(missing.issues.map((issue) => issue.code)).toContain("out_of_range");

  const duplicated = parseCandidateCsv(`${validCsv}\nRiver Road,42.110,-73.910,34,Greenfield County,0.7,0,2`);
  expect(duplicated.duplicate_count).toBe(1);
  expect(duplicated.invalid_count).toBe(1);

  render(<CsvUpload selection={{ file: new File([], "invalid.csv", { type: "text/csv" }), result: duplicated }} onChange={vi.fn()} />);
  expect(screen.getByRole("alert")).toHaveTextContent("Duplicate site: River Road");
  expect(screen.getByText("1 issue")).toBeInTheDocument();
});
