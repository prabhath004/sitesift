"""Ranking candidate sites — spec §8.1D.

Highest score first. Ties are broken deterministically rather than arbitrarily:
two sites that score the same must come back in the same order on every run, or
the ranking is not reproducible and the demo is not stable.

The chain, in order:

1. overall score, descending — the ranking the product asks for;
2. fewer fatal findings, then fewer high-severity findings — between equal
   scores, prefer the site with less to go wrong;
3. import order — the order the user gave us, which is the only remaining
   signal and is stable across runs.
"""

from dataclasses import dataclass

from app.models.candidate_site import CandidateSite
from app.schemas.common import FindingSeverity
from app.services.scoring import SiteScoringResult


@dataclass(frozen=True)
class RankedSite:
    rank: int
    site: CandidateSite
    result: SiteScoringResult


def rank_sites(scored: list[tuple[CandidateSite, SiteScoringResult]]) -> list[RankedSite]:
    ordered = sorted(scored, key=_ranking_key)
    return [
        RankedSite(rank=position, site=site, result=result)
        for position, (site, result) in enumerate(ordered, start=1)
    ]


def _ranking_key(entry: tuple[CandidateSite, SiteScoringResult]) -> tuple[int, int, int, int]:
    site, result = entry
    severities = [finding.severity for finding in result.findings]
    return (
        -result.overall_score,
        severities.count(FindingSeverity.FATAL),
        severities.count(FindingSeverity.HIGH),
        site.sequence,
    )
