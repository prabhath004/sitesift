/**
 * API client.
 *
 * One place that knows the backend's base URL and error shape. Feature code
 * should call `apiFetch` rather than `fetch` directly so that base URL, JSON
 * handling, and error semantics stay consistent.
 */

import type { HealthResponse } from "@/types/api";

/**
 * The backend base URL. `NEXT_PUBLIC_API_URL` is read at build time by Next,
 * so it must be present in the environment when the frontend is built or
 * started; the fallback keeps `npm run dev` working with no `.env`.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    // Status 0 means the request never reached the backend: it is not running,
    // or the port/base URL is wrong.
    throw new ApiError(`Could not reach the SiteSift API at ${API_BASE_URL}`, 0);
  }

  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed`, response.status);
  }

  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health", { cache: "no-store" });
}
