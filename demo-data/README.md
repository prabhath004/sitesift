# Demo data

Placeholder fixtures for the demo scenario in the specification (§7 — Hudson
Valley Community Solar, a 5 MW community-solar project with a 25-acre minimum).

## `candidate-sites.sample.csv`

The five synthetic sites from the spec, verbatim. Nothing imports this file yet;
the CSV import path is the backend-screening agent's work.

Columns:

| Column | Required | Notes |
| --- | --- | --- |
| `site_name` | yes | Unique within one upload |
| `latitude` | yes | −90 to 90 |
| `longitude` | yes | −180 to 180 |
| `acreage` | yes | Greater than zero |
| `jurisdiction` | yes | Free text |
| `road_distance_miles` | no | Precomputed demo value |
| `flood_overlap_percent` | no | Precomputed demo value |
| `wetland_overlap_percent` | no | Precomputed demo value |

The three optional columns stand in for geospatial lookups that a real system
would compute (PostGIS, flood and wetland layers). Precomputing them keeps the
prototype deterministic and offline — see spec §12.1.

## Not here yet

- `sample-zoning-ordinance.pdf` — the document-analysis agent adds a sample
  permitting document.
- A seeded demo loader ("Load Sample Solar Project", spec §24).

Sites in this file are synthetic. Coordinates are approximate and are not tied
to real parcels.
