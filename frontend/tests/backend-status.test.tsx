import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { BackendStatus } from "@/components/backend-status";
import type { HealthResponse } from "@/types/api";

const health: HealthResponse = {
  status: "ok",
  service: "SiteSift API",
  version: "0.1.0",
  environment: "test",
  database: "ok",
};

afterEach(() => {
  vi.unstubAllGlobals();
});

test("shows backend details once the health check succeeds", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => health } as Response),
  );

  render(<BackendStatus />);

  expect(await screen.findByText("Backend connected")).toBeInTheDocument();
  expect(screen.getByText("SiteSift API")).toBeInTheDocument();
});

test("shows an error state when the backend is unreachable", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));

  render(<BackendStatus />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Backend unreachable");
});
