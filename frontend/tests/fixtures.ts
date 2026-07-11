/**
 * Test data, recorded from the real backend by `scripts/record-fixtures.py`.
 *
 * Tests assert against values *derived from the fixture*, not against numbers
 * typed into the test. A test that hard-codes `88` passes happily while the
 * backend returns something else; a test that reads the score from the response
 * it rendered cannot.
 */

import fixtures from "@/lib/api/fixtures.json";
import type {
  DocumentAnalysis,
  ProjectDashboardItem,
  RiskFinding,
  ScreeningResults,
  SiteBrief,
  SiteDetail,
} from "@/types/api";

interface Fixtures {
  screening_run: ScreeningResults;
  dashboard: ProjectDashboardItem[];
  sites: Record<string, SiteDetail>;
  briefs: Record<string, SiteBrief>;
  findings: Record<string, RiskFinding[]>;
  document_analysis: DocumentAnalysis;
}

const data = fixtures as unknown as Fixtures;

export const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

export const demoRun = (): ScreeningResults => clone(data.screening_run);
export const demoDashboard = (): ProjectDashboardItem[] => clone(data.dashboard);
export const demoProject = () => clone(data.screening_run.project);
export const demoAnalysis = (): DocumentAnalysis => clone(data.document_analysis);

/** The five candidate sites, in rank order. */
export const demoCandidates = () => demoRun().results;

/** The top-ranked site's detail — the one with the analyzed ordinance. */
export const topSiteDetail = (): SiteDetail => {
  const siteId = data.screening_run.results[0].site.id;
  return clone(data.sites[siteId]);
};

export const siteDetail = (siteId: string): SiteDetail => clone(data.sites[siteId]);
export const siteBrief = (siteId: string): SiteBrief => clone(data.briefs[siteId]);
