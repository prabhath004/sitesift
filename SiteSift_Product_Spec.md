# SiteSift

> Evidence-backed site triage for renewable energy and power infrastructure projects.

**Project type:** Targeted portfolio prototype for the Paces Junior Software Engineer application  
**Recommended build time:** 8–12 focused hours  
**Primary demo:** 60–90 second recorded walkthrough  
**Status:** MVP specification

---

## 1. Product Summary

SiteSift is a lightweight site-screening workflow for renewable energy and power infrastructure developers.

A developer uploads several candidate project sites and defines basic project requirements. SiteSift then:

1. Normalizes and validates the site data.
2. Runs deterministic screening checks.
3. Ranks the candidate sites by viability and risk.
4. Analyzes one relevant permitting or zoning document.
5. Connects each extracted requirement to source evidence.
6. Produces a concise diligence brief for human review.

The product is deliberately **not a general-purpose chatbot**. It demonstrates how structured software, geospatial checks, document analysis, background jobs, and human review can work together in a production-style workflow.

---

## 2. One-Line Pitch

**SiteSift ranks proposed energy sites, surfaces major development risks, and turns permitting documents into evidence-backed next steps.**

---

## 3. Why This Project Fits Paces

The Paces role emphasizes:

- Python and SQL
- Data-intensive backend systems
- ETL and database work
- AI agents used in production workflows
- LangGraph and structured agent orchestration
- End-to-end feature ownership
- Fast execution in ambiguous startup environments
- Power-project and infrastructure development

SiteSift demonstrates those capabilities through one focused vertical slice:

```text
Candidate sites
      ↓
Validation and normalization
      ↓
Deterministic site checks
      ↓
Document-analysis workflow
      ↓
Transparent scoring
      ↓
Human review
      ↓
Diligence brief
```

The strongest signal is the engineering separation between:

- **Deterministic software** for measurable facts and rules
- **Agent-assisted analysis** for unstructured documents and synthesis
- **Human approval** for high-impact conclusions

---

## 4. Problem Statement

Power and renewable infrastructure developers often evaluate many proposed sites before investing in detailed engineering, permitting, interconnection studies, land agreements, and construction planning.

Early decisions may depend on fragmented information such as:

- Site acreage
- Project type and capacity
- Flood or wetland exposure
- Road and infrastructure proximity
- Local jurisdiction
- Zoning and permitting requirements
- Missing project information
- Potential fatal flaws

Manual screening is slow and difficult to audit. SiteSift provides a fast first-pass workflow that identifies promising sites and clearly shows why each site received its result.

---

## 5. Target User

### Primary user

A renewable energy or power-project development analyst who receives multiple proposed sites and needs to decide which ones deserve deeper diligence.

### Secondary user

A permitting, real estate, or project-development specialist who reviews extracted requirements before they are used in a decision.

---

## 6. MVP User Story

> As a project developer, I want to upload several candidate solar sites and my project requirements so that I can quickly rank the sites, identify major risks, inspect supporting evidence, and decide which site should move to deeper diligence.

---

## 7. Demo Scenario

Use one polished, controlled scenario.

### Project

```yaml
project_name: Hudson Valley Community Solar
project_type: community_solar
target_capacity_mw: 5
minimum_acres: 25
preferred_state: New York
maximum_flood_overlap_percent: 5
maximum_wetland_overlap_percent: 10
maximum_distance_to_road_miles: 2
```

### Candidate sites

Upload a CSV containing five synthetic or public-data-backed sites:

```csv
site_name,latitude,longitude,acreage,jurisdiction,road_distance_miles,flood_overlap_percent,wetland_overlap_percent
River Road,42.110,-73.910,34,Greenfield County,0.7,0,2
Oak Parcel,42.145,-73.880,27,Greenfield County,1.1,4,14
County Route 9,42.090,-73.970,22,Greenfield County,0.4,0,1
Mill Farm,42.180,-73.930,41,Greenfield County,2.8,7,4
North Ridge,42.125,-73.850,31,Greenfield County,1.3,2,5
```

### Expected result

- River Road: recommended
- North Ridge: recommended with review
- Oak Parcel: high wetland risk
- Mill Farm: flood and access risks
- County Route 9: insufficient acreage

The selected site is then evaluated against one sample zoning or permitting PDF.

---

## 8. Scope

## 8.1 Required MVP Features

### A. Project intake

The user can create a screening project with:

- Project name
- Project type
- Target capacity
- Minimum acreage
- State or target region
- Screening thresholds
- Optional notes

### B. Candidate-site upload

The user can:

- Upload a CSV
- Preview parsed rows
- See validation errors
- Confirm the import
- Start the screening run

Required CSV fields:

```text
site_name
latitude
longitude
acreage
jurisdiction
```

Optional precomputed demo fields:

```text
road_distance_miles
flood_overlap_percent
wetland_overlap_percent
```

### C. Deterministic screening

The backend calculates or reads:

- Acreage qualification
- Flood overlap
- Wetland overlap
- Road-distance qualification
- Missing required fields
- Number of high-risk findings
- Number of warning findings

All calculations must be reproducible without an LLM.

### D. Candidate ranking

Each site receives:

- Overall score from 0–100
- Recommendation status
- Category-level scores
- Finding count
- Short explanation
- Missing-information list

Statuses:

```text
Recommended
Recommended with review
Needs investigation
High risk
Reject
```

### E. Permitting-document analysis

For one selected site, the user can upload a sample zoning or permitting PDF.

The workflow extracts structured requirements such as:

- Whether the project type is permitted
- Approval type
- Minimum setbacks
- Public-hearing requirement
- Decommissioning-plan requirement
- Bond or financial-security requirement
- Required studies
- Missing or ambiguous requirements

Each extracted claim must include:

- Source document name
- Page number or section
- Supporting text excerpt
- Confidence score
- Review status

### F. Human review

A reviewer can:

- Approve a finding
- Edit a finding
- Reject a finding
- Add a note
- Mark it as requiring legal or domain review

### G. Diligence brief

Generate a printable web report containing:

- Project summary
- Candidate ranking
- Selected-site overview
- Positive signals
- Major risks
- Permitting requirements
- Missing information
- Recommended next steps
- Evidence references
- Review status

---

## 8.2 Explicit Non-Goals

Do not build these for the application prototype:

- Nationwide parcel coverage
- Real power-flow simulation
- Interconnection queue modeling
- Hosting-capacity analysis
- Utility-grade engineering calculations
- Automated legal conclusions
- A full GIS data platform
- Authentication and billing
- Multi-tenant enterprise permissions
- A general energy chatbot
- A complete clone of Paces

---

## 9. Product Principles

### 9.1 Evidence before confidence

Every document-derived conclusion must show where it came from.

### 9.2 Deterministic facts stay deterministic

An LLM should not calculate acreage, distance, overlap, threshold violations, or numeric scores.

### 9.3 Humans remain in control

A document-derived requirement is not considered final until a reviewer approves it.

### 9.4 Partial results are useful

If document analysis fails, deterministic site-screening results should remain available.

### 9.5 The score must be explainable

The user should be able to understand every deduction.

---

## 10. User Experience

## 10.1 Screen 1 — Project Dashboard

### Purpose

Show existing screening projects and let the user start a new one.

### Components

- Page title: `SiteSift`
- Subtitle: `Screen candidate sites before expensive diligence`
- `New Screening` button
- Summary cards:
  - Active screenings
  - Candidate sites
  - High-risk findings
  - Sites recommended
- Projects table:
  - Project
  - Project type
  - Candidate count
  - Top score
  - Status
  - Updated time

### Empty state

```text
No screening projects yet.

Upload candidate sites and generate an evidence-backed first-pass assessment.
```

---

## 10.2 Screen 2 — New Screening

### Section A: Project details

Fields:

- Project name
- Project type
- Target capacity
- Minimum acreage
- Target state
- Notes

Project types:

```text
Solar
Battery storage
Data center
EV charging
Other power infrastructure
```

### Section B: Screening criteria

Fields:

- Maximum flood overlap
- Maximum wetland overlap
- Maximum road distance
- Required acreage
- Custom rule notes

### Section C: Candidate upload

Features:

- Drag-and-drop CSV
- Download sample CSV
- Parsed-row preview
- Inline validation errors
- `Run Screening` button

---

## 10.3 Screen 3 — Screening Results

### Header

```text
Hudson Valley Community Solar
5 candidate sites screened
```

### Summary cards

- Recommended: 2
- Needs review: 1
- High risk: 1
- Rejected: 1

### Candidate table

| Site | Score | Status | High Risks | Warnings | Next Step |
|---|---:|---|---:|---:|---|
| River Road | 88 | Recommended | 0 | 1 | Review permitting |
| North Ridge | 79 | Recommended with review | 0 | 2 | Confirm site control |
| Oak Parcel | 61 | High risk | 1 | 1 | Investigate wetlands |
| Mill Farm | 47 | High risk | 2 | 1 | Review access and flood |
| County Route 9 | 35 | Reject | 1 | 0 | Insufficient acreage |

### Optional map

For the MVP, display simple markers using Leaflet or Mapbox.

Marker interaction shows:

- Site name
- Score
- Status
- Key risk

The map is useful but must not block completion of the core workflow.

---

## 10.4 Screen 4 — Site Detail

### Header

```text
River Road
Overall viability: 88/100
Recommended
```

### Score breakdown

```text
Site suitability:       24/25
Environmental:          23/25
Access and proximity:   21/25
Permitting readiness:   20/25
```

### Positive signals

```text
✓ 34 acres exceeds the 25-acre requirement
✓ No mapped flood overlap in the demo dataset
✓ Wetland overlap is below the configured threshold
✓ Road access is within the preferred distance
```

### Risks

```text
! Conditional-use approval may be required
! Decommissioning security requires human confirmation
```

### Missing information

```text
? Landowner site-control status
? Utility interconnection availability
? Current title or ownership report
```

### Actions

- Upload permitting document
- Run document analysis
- Generate brief
- Mark site for deeper diligence

---

## 10.5 Screen 5 — Document Evidence

### Workflow status

```text
✓ Document uploaded
✓ Text extracted
✓ Relevant sections retrieved
✓ Requirements structured
✓ Evidence validated
⚠ 1 requirement requires human review
```

### Requirement card

```text
Requirement: Conditional-use approval
Status: Needs review
Confidence: 91%

Evidence:
"Utility-scale solar energy systems may be permitted following
conditional-use approval by the Planning Board."

Source:
Greenfield County Zoning Ordinance
Section 4.3 — Page 84
```

Actions:

- Approve
- Edit
- Reject
- Escalate for expert review

Do not display private model reasoning or chain-of-thought. Display only:

- Workflow step
- Tool used
- Status
- Structured output
- Evidence
- Error information

---

## 10.6 Screen 6 — Diligence Brief

### Report structure

1. Executive summary
2. Project criteria
3. Candidate-site ranking
4. Selected-site overview
5. Positive signals
6. Critical risks
7. Permitting pathway
8. Missing information
9. Recommended next actions
10. Sources and review history

### Example recommendation

```text
River Road is the strongest candidate in the current screening set.
It satisfies the configured acreage, flood, wetland, and access thresholds.

Before deeper diligence, confirm:

1. Whether conditional-use approval applies to the proposed system size.
2. The required decommissioning security amount.
3. Landowner site control.
4. Utility interconnection availability.

This result is an early-screening assessment and not an engineering,
environmental, utility, or legal determination.
```

---

## 11. System Architecture

```text
┌──────────────────────────────┐
│ Next.js + TypeScript         │
│ Dashboard and review UI      │
└──────────────┬───────────────┘
               │ REST API
┌──────────────▼───────────────┐
│ FastAPI                      │
│ Validation and orchestration │
└───────┬──────────┬───────────┘
        │          │
        │          └─────────────────────┐
        │                                │
┌───────▼──────────┐          ┌──────────▼──────────┐
│ PostgreSQL       │          │ Background worker   │
│ Projects/results│          │ Screening + docs    │
└──────────────────┘          └──────────┬──────────┘
                                        │
                             ┌──────────▼──────────┐
                             │ LangGraph workflow │
                             │ Structured outputs │
                             └──────────┬──────────┘
                                        │
                             ┌──────────▼──────────┐
                             │ Object storage     │
                             │ PDFs and reports   │
                             └─────────────────────┘
```

### Recommended stack

```text
Frontend:       Next.js, TypeScript, Tailwind CSS
Backend:        FastAPI, Python, Pydantic
Database:       PostgreSQL, SQLAlchemy
Agent workflow: LangGraph
Document text:  PyMuPDF or pypdf
Retrieval:      Simple chunking + embeddings or keyword/BM25 retrieval
Jobs:           Redis + RQ, Celery, or Dramatiq
Maps:           React Leaflet or Mapbox
Deployment:     Vercel + Render/Railway/Fly.io
Containers:     Docker
Testing:        Pytest + Playwright or React Testing Library
```

For an 8–12 hour prototype, synchronous execution is acceptable initially. Add a job table and simulated background statuses if a real queue would jeopardize completion.

---

## 12. Deterministic and Agent Responsibilities

## 12.1 Deterministic layer

Use normal code for:

- CSV validation
- Coordinate validation
- Unit normalization
- Acreage comparison
- Flood and wetland threshold checks
- Road-distance comparison
- Category scoring
- Final weighted-score calculation
- Status assignment
- Missing-field detection
- Sorting and ranking
- Report totals
- Idempotency checks

## 12.2 Agent-assisted layer

Use LangGraph or structured LLM calls for:

- Classifying relevant ordinance sections
- Extracting permitting requirements
- Identifying ambiguity
- Converting text into a fixed schema
- Summarizing approved findings
- Suggesting next investigative steps

## 12.3 Human layer

Require human review for:

- Legal or regulatory interpretations
- Ambiguous permitting language
- Requirements with weak evidence
- Conflicting source sections
- Fatal-flaw conclusions based on documents
- Final approval of the diligence brief

---

## 13. LangGraph Workflow

```text
START
  ↓
Validate document
  ↓
Extract text
  ↓
Split into page-aware sections
  ↓
Retrieve sections relevant to project type
  ↓
Extract structured requirements
  ↓
Validate evidence and page references
  ↓
Assign confidence and review status
  ↓
Persist findings
  ↓
Generate summary from approved findings
  ↓
END
```

### Suggested nodes

```text
validate_document
extract_text
classify_document
retrieve_relevant_sections
extract_requirements
validate_citations
flag_ambiguity
persist_findings
generate_summary
```

### Workflow state

```python
from typing import TypedDict

class AnalysisState(TypedDict):
    project_id: str
    site_id: str
    document_id: str
    document_text: str
    page_chunks: list[dict]
    relevant_sections: list[dict]
    extracted_requirements: list[dict]
    validation_errors: list[str]
    final_findings: list[dict]
    status: str
```

### Structured requirement schema

```python
from pydantic import BaseModel, Field
from typing import Literal

class Evidence(BaseModel):
    document_name: str
    page_number: int | None
    section_name: str | None
    excerpt: str

class PermittingRequirement(BaseModel):
    category: Literal[
        "use_permission",
        "setback",
        "public_hearing",
        "decommissioning",
        "financial_security",
        "study",
        "application",
        "other",
    ]
    title: str
    description: str
    value: str | None
    severity: Literal["info", "warning", "high", "fatal"]
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence]
    requires_human_review: bool
```

---

## 14. Scoring Model

Use a transparent weighted score.

```text
Overall score =
    25% Site suitability
  + 25% Environmental
  + 25% Access and proximity
  + 25% Permitting readiness
```

### Example scoring rules

#### Site suitability — 25 points

```text
Acreage >= required acreage:                  +25
Acreage 90–99% of requirement:                +15
Acreage 75–89% of requirement:                 +8
Acreage <75% of requirement:                   +0
```

#### Environmental — 25 points

```text
Flood overlap <= configured threshold:        +12
Flood overlap slightly over threshold:         +6
Flood overlap materially over threshold:       +0

Wetland overlap <= configured threshold:      +13
Wetland overlap slightly over threshold:       +7
Wetland overlap materially over threshold:     +0
```

#### Access and proximity — 25 points

```text
Road distance <= preferred distance:          +25
Road distance <= 1.5x preferred distance:     +15
Road distance > 1.5x preferred distance:       +5
```

#### Permitting readiness — 25 points

```text
Use appears permitted by right:               +25
Conditional or special-use approval:          +18
Ambiguous or missing ordinance evidence:      +10
Use appears prohibited:                        +0
```

### Status rules

```python
if fatal_findings > 0:
    status = "Reject"
elif score >= 80:
    status = "Recommended"
elif score >= 70:
    status = "Recommended with review"
elif score >= 55:
    status = "Needs investigation"
else:
    status = "High risk"
```

Always show the exact score deductions in the UI.

---

## 15. Data Model

## 15.1 `projects`

```text
id
name
project_type
target_capacity_mw
minimum_acres
target_state
screening_criteria_json
notes
status
created_at
updated_at
```

## 15.2 `candidate_sites`

```text
id
project_id
name
latitude
longitude
acreage
jurisdiction
raw_input_json
created_at
```

## 15.3 `screening_runs`

```text
id
project_id
status
idempotency_key
started_at
completed_at
error_message
```

## 15.4 `site_scores`

```text
id
screening_run_id
site_id
overall_score
site_suitability_score
environmental_score
access_score
permitting_score
recommendation_status
explanation
created_at
```

## 15.5 `risk_findings`

```text
id
site_id
screening_run_id
source_type
category
title
description
severity
value
confidence
review_status
created_at
updated_at
```

`source_type` values:

```text
deterministic
document
human
```

## 15.6 `documents`

```text
id
project_id
site_id
filename
storage_path
mime_type
page_count
processing_status
created_at
```

## 15.7 `evidence`

```text
id
finding_id
document_id
page_number
section_name
excerpt
created_at
```

## 15.8 `reviews`

```text
id
finding_id
decision
edited_title
edited_description
reviewer_note
created_at
```

## 15.9 `workflow_events`

```text
id
screening_run_id
step_name
status
input_summary
output_summary
duration_ms
error_message
created_at
```

---

## 16. API Specification

## 16.1 Projects

```http
POST /api/projects
GET  /api/projects
GET  /api/projects/{project_id}
```

### Create project request

```json
{
  "name": "Hudson Valley Community Solar",
  "project_type": "community_solar",
  "target_capacity_mw": 5,
  "minimum_acres": 25,
  "target_state": "NY",
  "screening_criteria": {
    "maximum_flood_overlap_percent": 5,
    "maximum_wetland_overlap_percent": 10,
    "maximum_road_distance_miles": 2
  }
}
```

## 16.2 Candidate sites

```http
POST /api/projects/{project_id}/sites/import
GET  /api/projects/{project_id}/sites
GET  /api/sites/{site_id}
```

## 16.3 Screening

```http
POST /api/projects/{project_id}/screenings
GET  /api/screenings/{screening_id}
GET  /api/screenings/{screening_id}/events
```

## 16.4 Documents

```http
POST /api/sites/{site_id}/documents
POST /api/documents/{document_id}/analyze
GET  /api/documents/{document_id}/analysis
```

## 16.5 Findings and review

```http
GET   /api/sites/{site_id}/findings
PATCH /api/findings/{finding_id}/review
```

### Review request

```json
{
  "decision": "approved",
  "reviewer_note": "Confirmed against Section 4.3."
}
```

## 16.6 Report

```http
POST /api/sites/{site_id}/brief
GET  /api/sites/{site_id}/brief
```

---

## 17. Validation Rules

### CSV validation

Reject or flag rows when:

- Site name is missing
- Latitude is outside `-90` to `90`
- Longitude is outside `-180` to `180`
- Acreage is zero or negative
- Numeric values cannot be parsed
- A duplicate site appears in the same upload

### Document validation

Reject or flag when:

- File is not a PDF
- File exceeds the configured size
- No extractable text is found
- Page extraction fails
- The document contains no relevant sections
- Evidence page references cannot be verified

### Safe behavior

The system must state:

```text
SiteSift provides an early-screening prototype. Results are not legal,
environmental, engineering, utility, title, or investment advice and
must be validated by qualified professionals.
```

---

## 18. Reliability Requirements

### Idempotency

A repeated screening request with the same idempotency key should not create duplicate runs.

### Retry behavior

Retry transient failures for:

- Document parsing
- Model API timeouts
- Temporary database errors

Do not retry:

- Invalid files
- Invalid schemas
- Missing required input
- Unsupported document types

### Partial completion

A run can have these statuses:

```text
queued
screening
document_analysis
needs_review
completed
partially_completed
failed
```

If document analysis fails, site scores and deterministic findings remain visible.

### Auditability

Record:

- Workflow step
- Start and completion time
- Duration
- Success or failure
- Error message
- Model and prompt version where applicable
- Finding review history

---

## 19. Observability

At minimum, log:

```text
request_id
project_id
site_id
screening_run_id
workflow_step
status
duration_ms
error_type
```

Optional dashboard metrics:

- Screening runs completed
- Average screening duration
- Document-analysis success rate
- Findings requiring review
- Average model latency
- Average token usage

Avoid logging full uploaded documents or sensitive user content by default.

---

## 20. Testing Requirements

### Backend unit tests

Test:

- CSV validation
- Score calculations
- Threshold boundary cases
- Status assignment
- Duplicate-run prevention
- Requirement-schema validation

### Integration tests

Test:

- Create project → import sites → run screening
- Upload PDF → analyze → persist evidence
- Approve finding → regenerate brief
- Document failure → deterministic results remain available

### Frontend tests

Test:

- Invalid CSV errors
- Result-table sorting
- Site-detail rendering
- Review action
- Loading and failure states

### Minimum acceptance test

```text
Given a valid project and five candidate sites,
when the user runs SiteSift,
then all five sites receive transparent scores,
the candidates are ranked,
and each deduction can be inspected.

Given a selected site and a zoning PDF,
when document analysis finishes,
then structured requirements are displayed with page-level evidence
and can be approved or rejected by a human reviewer.
```

---

## 21. Suggested Repository Structure

```text
sitesift/
├── README.md
├── docker-compose.yml
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── projects/new/page.tsx
│   │   ├── projects/[id]/page.tsx
│   │   └── sites/[id]/page.tsx
│   ├── components/
│   ├── lib/
│   └── types/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── csv_import.py
│   │   │   ├── scoring.py
│   │   │   ├── document_parser.py
│   │   │   └── report_generator.py
│   │   ├── workflows/
│   │   │   └── permitting_graph.py
│   │   └── observability/
│   └── tests/
├── demo-data/
│   ├── candidate-sites.csv
│   └── sample-zoning-ordinance.pdf
└── docs/
    ├── architecture.md
    └── demo-script.md
```

---

## 22. Build Plan

The project should be built in priority order. Stop when the end-to-end demo is convincing.

### Phase 1 — Core data workflow

- Create project form
- Upload and validate CSV
- Store sites
- Implement deterministic score
- Show ranked results

### Phase 2 — Site detail

- Show score breakdown
- Show positive signals
- Show risks
- Show missing information

### Phase 3 — Document analysis

- Upload one PDF
- Extract page-aware text
- Retrieve relevant sections
- Produce structured requirements
- Attach page evidence

### Phase 4 — Human review and brief

- Approve, edit, or reject findings
- Generate concise diligence brief
- Display workflow events

### Phase 5 — Polish

- Loading states
- Error states
- Seeded demo button
- Responsive layout
- Deployment
- README
- Video recording

---

## 23. Time-Boxed Implementation Plan

### Hours 1–2

- Set up Next.js and FastAPI
- Create database models
- Build seeded demo data
- Implement project creation

### Hours 3–4

- Implement CSV import
- Implement scoring rules
- Build results table

### Hours 5–6

- Build site-detail page
- Add score explanations
- Add simple map if time permits

### Hours 7–8

- Add PDF upload
- Implement page-aware extraction
- Add structured document-analysis call

### Hours 9–10

- Add evidence cards
- Add approve/edit/reject actions
- Generate brief

### Hours 11–12

- Add workflow-event timeline
- Test the demo path
- Deploy
- Record video
- Send outreach

---

## 24. Seeded Demo Mode

Add a prominent button:

```text
Load Sample Solar Project
```

It should create:

- One project
- Five candidate sites
- Precomputed deterministic inputs
- One sample permitting document
- One completed or ready-to-run analysis

This guarantees that the reviewer can understand the product immediately without preparing data.

---

## 25. Visual Direction

### Style

- Clean
- Technical
- Map-oriented
- Evidence-first
- Minimal animation
- High information density without clutter

### Suggested visual hierarchy

```text
Large viability score
Clear recommendation badge
Compact score breakdown
Risk cards by severity
Evidence cards with page references
Simple workflow timeline
```

### Suggested labels

```text
Fatal flaw
High risk
Needs review
Verified
Missing information
Recommended
```

Avoid excessive gradients, glowing AI effects, chatbot bubbles, or generic “agent” imagery.

---

## 26. Demo Video Script

### 0–12 seconds — Problem

> Power-project developers may receive many proposed sites, but early screening requires checking fragmented site, environmental, and permitting information. I built SiteSift to automate the first pass.

### 12–25 seconds — Intake

> I define a five-megawatt community-solar project, set its acreage and risk thresholds, and upload five candidate sites.

Show:

- Project criteria
- CSV upload
- `Run Screening`

### 25–42 seconds — Ranking

> SiteSift validates the data, applies deterministic screening rules, and ranks the sites with a fully explainable score.

Show:

- Candidate table
- Status badges
- Score breakdown

### 42–62 seconds — Site detail

> River Road ranks first. I can see why: it meets the acreage requirement, stays below the environmental thresholds, and has acceptable access. Missing information is kept separate from confirmed risks.

Show:

- Positive signals
- Risks
- Missing information

### 62–80 seconds — Document evidence

> For permitting, a LangGraph workflow extracts structured requirements from the zoning document. Every claim is connected to its source page and sent through human review.

Show:

- Workflow steps
- Requirement card
- Source excerpt
- Approve action

### 80–90 seconds — Architecture and close

> The frontend is Next.js, the backend is FastAPI and PostgreSQL, deterministic checks remain normal code, and LangGraph is used only for unstructured document analysis. I built this as a small exploration of the workflows Paces is solving.

Show:

```text
Next.js → FastAPI → PostgreSQL
                  → Screening engine
                  → LangGraph
                  → Human review
```

---

## 27. Outreach Message

```text
Hi [Name] — I applied for the Junior Software Engineer role and spent
some time understanding the power-project diligence workflow described
by Paces.

I built SiteSift, a small prototype that ranks candidate project sites,
surfaces early risks, and extracts evidence-backed permitting requirements
for human review. I intentionally kept measurable site checks deterministic
and used LangGraph only for unstructured document analysis.

90-second demo: [Loom]
Live prototype: [URL]
GitHub: [URL]

I would love to learn how your team approaches these workflows at
production scale.
```

---

## 28. README Opening

```markdown
# SiteSift

Evidence-backed site triage for renewable energy and power infrastructure.

SiteSift accepts candidate project sites, applies transparent screening
rules, ranks the sites, and extracts permitting requirements from supporting
documents with page-level evidence and human review.

## Why I built it

I created SiteSift as a focused exploration of software workflows used in
early-stage power-project development. The goal was not to reproduce a
commercial diligence platform, but to demonstrate a reliable architecture
for combining deterministic data processing, document analysis, structured
agent workflows, and expert review.
```

---

## 29. Strong Technical Talking Points

Be prepared to explain:

1. Why numeric and geospatial checks are deterministic.
2. Why document interpretation requires structured outputs and evidence.
3. How the workflow handles model failure.
4. How page-level citations are validated.
5. Why human approval is required.
6. How idempotency prevents duplicate screening runs.
7. How the system could scale from synchronous execution to queued workers.
8. How PostGIS could replace precomputed demo values.
9. How prompt and model versions would be audited.
10. How domain experts could correct findings and improve future workflows.

---

## 30. Stretch Goals

Only add these after the complete MVP works:

- PostGIS spatial intersection
- Public flood-zone data
- Public wetland data
- Parcel-boundary visualization
- Batch document processing
- Export to PDF
- Compare two sites side by side
- Saved screening templates
- Webhook on completion
- Evaluation dataset for extraction accuracy
- Rule versioning
- Reviewer analytics

---

## 31. Final Completion Checklist

### Product

- [ ] Seeded demo works
- [ ] Five candidates are ranked
- [ ] Every score is explainable
- [ ] One PDF can be analyzed
- [ ] Each extracted requirement has evidence
- [ ] Human review works
- [ ] Diligence brief is generated
- [ ] Loading and error states exist

### Engineering

- [ ] Python and FastAPI backend
- [ ] PostgreSQL data model
- [ ] Structured Pydantic outputs
- [ ] LangGraph workflow
- [ ] Idempotent screening request
- [ ] Workflow-event log
- [ ] Basic tests
- [ ] Docker setup
- [ ] Clear README

### Application

- [ ] Apply before waiting for project completion
- [ ] Deploy the prototype
- [ ] Record a 60–90 second demo
- [ ] Pin the GitHub repository
- [ ] Send concise outreach
- [ ] Do not spend more than one focused weekend

---

## 32. Definition of Done

SiteSift is complete when a reviewer can open the deployed application and, in under two minutes:

1. Load the sample project.
2. View five ranked candidate sites.
3. Understand why one site ranks above another.
4. Open a selected site.
5. Inspect a permitting requirement with page-level evidence.
6. Approve the finding.
7. View the updated diligence brief.

Anything beyond that is optional.
