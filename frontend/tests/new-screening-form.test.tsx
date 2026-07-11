import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { NewScreeningForm, validateProjectForm } from "@/components/forms/new-screening-form";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

test("validates required and numeric project fields before calling the API", () => {
  const api = { createProject: vi.fn(), importCandidateSites: vi.fn(), runScreening: vi.fn() };
  render(<NewScreeningForm api={api} />);
  fireEvent.click(screen.getByRole("button", { name: "Run Screening" }));

  expect(screen.getByText("Project name is required.")).toBeInTheDocument();
  expect(screen.getByText("Project type is required.")).toBeInTheDocument();
  expect(screen.getByText("Target capacity is required.")).toBeInTheDocument();
  expect(screen.getByText("A candidate-site CSV is required.")).toBeInTheDocument();
  expect(api.createProject).not.toHaveBeenCalled();
});

test("rejects out-of-range thresholds", () => {
  const errors = validateProjectForm({
    name: "Test",
    project_type: "solar",
    target_capacity_mw: "5",
    minimum_acres: "25",
    target_state: "NY",
    maximum_flood_overlap_percent: "101",
    maximum_wetland_overlap_percent: "-1",
    maximum_road_distance_miles: "0",
    notes: "",
  });
  expect(errors.maximum_flood_overlap_percent).toContain("between 0 and 100");
  expect(errors.maximum_wetland_overlap_percent).toContain("between 0 and 100");
  expect(errors.maximum_road_distance_miles).toContain("greater than 0");
});
