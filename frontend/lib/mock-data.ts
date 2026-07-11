import type {
  CandidateSite,
  Project,
  RiskFinding,
  ScoreExplanationItem,
  ScreeningRun,
  SiteDetail,
  SiteScore,
} from "@/types/api";

export const DEMO_PROJECT_ID = "11111111-1111-4111-8111-111111111111";
export const DEMO_SCREENING_ID = "22222222-2222-4222-8222-222222222222";

const timestamp = "2026-07-11T16:00:00Z";

export const demoProject: Project = {
  id: DEMO_PROJECT_ID,
  name: "Hudson Valley Community Solar",
  project_type: "community_solar",
  target_capacity_mw: 5,
  minimum_acres: 25,
  target_state: "NY",
  screening_criteria: {
    maximum_flood_overlap_percent: 5,
    maximum_wetland_overlap_percent: 10,
    maximum_road_distance_miles: 2,
  },
  notes: "Seeded demonstration project using synthetic candidate-site data.",
  status: "completed",
  created_at: timestamp,
  updated_at: timestamp,
};

export const demoScreeningRun: ScreeningRun = {
  id: DEMO_SCREENING_ID,
  project_id: DEMO_PROJECT_ID,
  status: "completed",
  idempotency_key: "seeded-solar-demo",
  started_at: "2026-07-11T15:59:42Z",
  completed_at: timestamp,
  error_message: null,
};

const siteRows = [
  ["River Road", 42.11, -73.91, 34, 0.7, 0, 2],
  ["North Ridge", 42.125, -73.85, 31, 1.3, 2, 5],
  ["Oak Parcel", 42.145, -73.88, 27, 1.1, 4, 14],
  ["Mill Farm", 42.18, -73.93, 41, 2.8, 7, 4],
  ["County Route 9", 42.09, -73.97, 22, 0.4, 0, 1],
] as const;

export const demoSites: CandidateSite[] = siteRows.map(
  ([name, latitude, longitude, acreage, road, flood, wetland], index) => ({
    id: `30000000-0000-4000-8000-00000000000${index + 1}`,
    project_id: DEMO_PROJECT_ID,
    name,
    latitude,
    longitude,
    acreage,
    jurisdiction: "Greenfield County",
    road_distance_miles: road,
    flood_overlap_percent: flood,
    wetland_overlap_percent: wetland,
    created_at: timestamp,
  }),
);

const scoreProfiles = [
  [88, 24, 23, 21, 20, "recommended"],
  [79, 22, 20, 19, 18, "recommended_with_review"],
  [61, 21, 13, 17, 10, "high_risk"],
  [47, 25, 10, 7, 5, "high_risk"],
  [35, 8, 22, 5, 0, "reject"],
] as const;

export const demoScores: SiteScore[] = scoreProfiles.map(
  ([overall, suitability, environmental, access, permitting, status], index) => ({
    id: `40000000-0000-4000-8000-00000000000${index + 1}`,
    screening_run_id: DEMO_SCREENING_ID,
    site_id: demoSites[index].id,
    overall_score: overall,
    site_suitability_score: suitability,
    environmental_score: environmental,
    access_score: access,
    permitting_score: permitting,
    recommendation_status: status,
    explanation:
      "Category rules are itemized in the score explanation. Permitting readiness remains pending document analysis.",
    created_at: timestamp,
  }),
);

const profileCopy = <T,>(values: T[]): T[] => [...values];

const positives = [
  [
    "34 acres exceeds the 25-acre requirement",
    "No mapped flood overlap in the demo dataset",
    "Wetland overlap is below the configured threshold",
    "Road distance is within the preferred threshold",
  ],
  [
    "31 acres exceeds the configured minimum",
    "Flood and wetland overlap are below thresholds",
    "Road distance is within the preferred threshold",
  ],
  ["27 acres meets the configured minimum", "Road distance and flood overlap meet thresholds"],
  ["41 acres provides strong site-area headroom", "Wetland overlap is below threshold"],
  ["No mapped flood overlap in the demo dataset", "Road distance is within the preferred threshold"],
];

const missing = [
  ["Landowner site-control status", "Utility interconnection availability", "Current title or ownership report"],
  ["Site-control agreement", "Utility feeder capacity", "Permitting pathway"],
  ["Wetland delineation", "Seasonal field survey", "Permitting pathway"],
  ["All-weather access design", "Flood mitigation study", "Permitting pathway"],
  ["Parcel expansion options", "Site-control status", "Permitting pathway"],
];

const findingDefinitions: Array<Array<[string, string, "info" | "warning" | "high" | "fatal", string]>> = [
  [["Access", "Road entrance geometry is unverified", "warning", "Mapped proximity is favorable, but entrance geometry requires field confirmation."]],
  [
    ["Site control", "Site-control evidence is missing", "warning", "No landowner option or lease record is included."],
    ["Access", "Driveway feasibility needs review", "warning", "Confirm a viable entrance before deeper diligence."],
  ],
  [
    ["Environmental", "Wetland overlap exceeds threshold", "high", "Mapped wetland overlap is 14% against a 10% maximum."],
    ["Environmental", "Wetland delineation is missing", "warning", "Desktop overlap should be confirmed with a field delineation."],
  ],
  [
    ["Environmental", "Flood overlap exceeds threshold", "high", "Mapped flood overlap is 7% against a 5% maximum."],
    ["Access", "Road distance exceeds threshold", "high", "Road distance is 2.8 miles against a 2-mile maximum."],
    ["Access", "Access route is unverified", "warning", "Legal and all-weather access have not been confirmed."],
  ],
  [["Site suitability", "Acreage is below the minimum", "fatal", "22 acres does not meet the 25-acre requirement."]],
];

export const demoFindings: RiskFinding[] = findingDefinitions.flatMap((definitions, siteIndex) =>
  definitions.map(([category, title, severity, description], findingIndex) => ({
    id: `50000000-0000-4000-8${siteIndex}00-00000000000${findingIndex + 1}`,
    site_id: demoSites[siteIndex].id,
    screening_run_id: DEMO_SCREENING_ID,
    source_type: "deterministic",
    category,
    title,
    description,
    severity,
    value: null,
    confidence: null,
    review_status: "pending",
    evidence: [],
    created_at: timestamp,
    updated_at: timestamp,
  })),
);

function severityFor(points: number): "info" | "warning" | "high" | "fatal" {
  if (points === 25) return "info";
  if (points >= 18) return "warning";
  if (points > 0) return "high";
  return "fatal";
}

export function explanationsFor(site: CandidateSite, score: SiteScore, project = demoProject): ScoreExplanationItem[] {
  const criteria = project.screening_criteria;
  return [
    {
      id: `${site.id}-suitability`,
      category: "Site suitability",
      rule: "Minimum usable acreage",
      actual_value: `${site.acreage} acres`,
      threshold: `At least ${project.minimum_acres} acres`,
      points_possible: 25,
      points_awarded: score.site_suitability_score,
      severity: severityFor(score.site_suitability_score),
      explanation:
        site.acreage >= project.minimum_acres
          ? "The site meets the configured acreage requirement; any held points reflect remaining parcel verification."
          : "The site does not meet the configured acreage requirement.",
    },
    {
      id: `${site.id}-environmental`,
      category: "Environmental",
      rule: "Flood and wetland overlap",
      actual_value: `${site.flood_overlap_percent ?? "Missing"}% flood · ${site.wetland_overlap_percent ?? "Missing"}% wetland`,
      threshold: `≤ ${criteria.maximum_flood_overlap_percent}% flood · ≤ ${criteria.maximum_wetland_overlap_percent}% wetland`,
      points_possible: 25,
      points_awarded: score.environmental_score,
      severity: severityFor(score.environmental_score),
      explanation: "Mapped overlaps are compared directly with the project’s configured thresholds.",
    },
    {
      id: `${site.id}-access`,
      category: "Access and proximity",
      rule: "Distance to mapped road",
      actual_value: site.road_distance_miles === null ? "Missing" : `${site.road_distance_miles} miles`,
      threshold: `≤ ${criteria.maximum_road_distance_miles} miles`,
      points_possible: 25,
      points_awarded: score.access_score,
      severity: severityFor(score.access_score),
      explanation: "Road proximity is deterministic; legal access and entrance geometry remain separate diligence items.",
    },
    {
      id: `${site.id}-permitting`,
      category: "Permitting readiness",
      rule: "Local use and approval pathway",
      actual_value: "Pending document analysis",
      threshold: "Verified local permitting evidence",
      points_possible: 25,
      points_awarded: score.permitting_score,
      severity: score.permitting_score === 0 ? "high" : "warning",
      explanation:
        "No permitting document has been analyzed. This provisional category value is mock screening data, not a permitting conclusion.",
    },
  ];
}

export const nextActions = [
  "Review permitting",
  "Confirm site control",
  "Investigate wetlands",
  "Review access and flood",
  "Insufficient acreage",
];

export const demoSiteDetails: SiteDetail[] = demoSites.map((site, index) => ({
  project: demoProject,
  site,
  score: demoScores[index],
  rank: index + 1,
  positive_signals: profileCopy(positives[index]),
  risks: demoFindings.filter((finding) => finding.site_id === site.id),
  missing_information: profileCopy(missing[index]),
  explanations: explanationsFor(site, demoScores[index]),
}));
