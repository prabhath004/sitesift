/**
 * The API boundary. Components import `siteSiftApi` from here and never call
 * `fetch` themselves.
 *
 * The integrated app talks to the real backend. The mock is opt-in, explicit, and
 * off unless `NEXT_PUBLIC_USE_MOCK_API=true` — and a failing request never falls
 * back to it. Silently serving fabricated scores when the backend is down would
 * make an outage look like a screening result, which is the one failure mode this
 * product cannot have.
 */

import { httpApi, ApiError, API_BASE_URL, type SiteSiftApi } from "@/lib/api/client";
import { mockApi, resetMockApi } from "@/lib/api/mock";

export const USE_MOCK_API = process.env.NEXT_PUBLIC_USE_MOCK_API === "true";

export const siteSiftApi: SiteSiftApi = USE_MOCK_API ? mockApi : httpApi;

export { ApiError, API_BASE_URL, httpApi, mockApi, resetMockApi };
export type { SiteSiftApi };
