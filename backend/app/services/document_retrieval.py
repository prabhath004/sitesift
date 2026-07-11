"""Deterministic retrieval over page-aware document chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.document import DocumentChunk
from app.schemas.finding import RequirementCategory


@dataclass(frozen=True)
class RetrievedSection:
    chunk_id: str
    page_number: int
    section_heading: str | None
    text: str
    score: int
    matched_terms: list[str]


BASE_TERMS: tuple[str, ...] = (
    "solar",
    "energy",
    "permit",
    "conditional",
    "special use",
    "setback",
    "hearing",
    "decommission",
    "financial security",
    "bond",
    "study",
    "traffic",
    "environmental",
    "application",
)

CATEGORY_TERMS: dict[RequirementCategory, tuple[str, ...]] = {
    RequirementCategory.USE_PERMISSION: ("permitted", "conditional", "special use", "approval"),
    RequirementCategory.SETBACK: ("setback", "feet", "foot"),
    RequirementCategory.PUBLIC_HEARING: ("public hearing", "hearing"),
    RequirementCategory.DECOMMISSIONING: ("decommission", "removal plan"),
    RequirementCategory.FINANCIAL_SECURITY: ("bond", "financial security", "surety"),
    RequirementCategory.ENVIRONMENTAL_STUDY: ("environmental", "wetland", "study"),
    RequirementCategory.TRAFFIC_STUDY: ("traffic", "road", "study"),
    RequirementCategory.APPLICATION_REQUIREMENT: ("application", "site plan", "submission"),
    RequirementCategory.OTHER: (),
}


def retrieve_relevant_sections(
    chunks: list[DocumentChunk],
    *,
    project_type: str,
    limit: int = 8,
) -> list[RetrievedSection]:
    """Return chunks whose text matches permitting-related keywords."""
    project_terms = project_type.replace("_", " ").split()
    terms = set(BASE_TERMS).union(project_terms)
    for category_terms in CATEGORY_TERMS.values():
        terms.update(category_terms)

    scored: list[RetrievedSection] = []
    for chunk in chunks:
        normalized = chunk.normalized_text.lower()
        matched_terms = sorted(term for term in terms if _term_matches(term, normalized))
        if not matched_terms:
            continue
        score = sum(3 if " " in term else 1 for term in matched_terms)
        scored.append(
            RetrievedSection(
                chunk_id=chunk.id,
                page_number=chunk.page_number,
                section_heading=chunk.section_heading,
                text=chunk.text,
                score=score,
                matched_terms=matched_terms,
            )
        )

    scored.sort(key=lambda item: (-item.score, item.page_number))
    return scored[:limit]


def _term_matches(term: str, text: str) -> bool:
    if " " in term:
        return term in text
    return re.search(rf"\b{re.escape(term)}\b", text) is not None
