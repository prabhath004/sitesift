# Frontend integration notes

The frontend vertical slice currently uses the typed mock implementation behind
`frontend/lib/api.ts`. Pages depend on the `SiteSiftApi` interface so an HTTP
implementation can replace the mock without changing page components.

## Contract assumptions

1. `GET /api/projects` defines `Project[]`, but the dashboard also needs candidate
   totals, top score, finding totals, and recommendation totals. The adapter
   composes a frontend-only `ProjectDashboardItem` from documented entities. The
   integration branch must decide whether to make multiple documented calls or
   propose a dashboard summary endpoint.
2. The CSV import response is described as parsed rows plus per-row validation
   errors, but its exact envelope is not specified. The mock returns imported
   `CandidateSite[]` plus imported/rejected counts. Client-side preview errors are
   not treated as a backend schema.
3. `SiteScore.explanation` is a string, while the product requires each deduction
   to expose category, rule, actual value, threshold, points possible, points
   awarded, severity, and explanation. `ScoreExplanationItem` is therefore an
   adapter-only parsed view model. The backend will need to encode a stable,
   machine-readable explanation or the contract will need an additive shape.
4. `Project.status` is an unconstrained string. The dashboard currently treats
   every project except `failed` as active and displays the received value.
5. There is no defined response for combined ranking results or site-detail data.
   `ScreeningResults` and `SiteDetail` are adapter compositions of documented
   Project, CandidateSite, ScreeningRun, SiteScore, and RiskFinding entities.
6. The specification contains score examples that do not strictly follow the
   example rules (River Road is 24/25 for acreage despite exceeding the minimum,
   for example). Seeded values preserve the specified overall/category scores so
   that 88 is consistent across dashboard, ranking, and site detail.
7. The permitting score is present in the draft SiteScore contract before
   document analysis. The UI labels it as provisional and always states
   **Pending document analysis**. It makes no permitting claim.
8. Both `solar` and `community_solar` remain accepted types as required by the
   contract open question. The create form offers the five product-requested
   labels and maps Solar to `solar`; the seeded sample uses `community_solar`.
9. Sorting and status filtering are client-side because v1 explicitly leaves
   server pagination/filtering/sorting undefined.

## Intentionally deferred to integration

- Replace `mockApi` with real HTTP requests and multipart upload handling.
- Reconcile the adapter-only CSV/result/detail compositions with implemented
  backend response envelopes without silently changing shared schemas.
- Enable permitting-document upload and analysis once those endpoints exist.
- Add document evidence, human review, and diligence brief routes in their
  owning/integration work once real workflow data is available.
- Decide persistence and cache behavior for newly created client-side mock
  projects; the current in-memory store is intentionally demo-only.
