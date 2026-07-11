"""Requirement extraction interfaces and deterministic fallback extractor."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Protocol

from pydantic import ValidationError

from app.schemas.common import FindingSeverity
from app.schemas.document import ExtractedRequirement
from app.schemas.finding import RequirementCategory
from app.services.document_errors import InvalidModelOutputError
from app.services.document_retrieval import RetrievedSection


class RequirementExtractor(Protocol):
    """Interface for LLM-backed or mocked requirement extractors."""

    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        """Return raw structured requirements."""


class HeuristicRequirementExtractor:
    """Local extractor used when no model provider is configured.

    It keeps tests and local demos free of API keys while preserving the same
    structured-output validation path a model-backed extractor would use.
    """

    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        requirements: list[dict[str, Any]] = []
        for section in sections:
            text = section.text
            requirements.extend(self._extract_from_section(section, text))
        return dedupe_requirements(requirements)

    def _extract_from_section(self, section: RetrievedSection, text: str) -> list[dict[str, Any]]:
        lowered = text.lower()
        extracted: list[dict[str, Any]] = []

        if "conditional-use" in lowered or "conditional use" in lowered:
            extracted.append(
                self._requirement(
                    section,
                    category=RequirementCategory.USE_PERMISSION,
                    title="Conditional-use approval",
                    description=(
                        "The document indicates that the project may require "
                        "conditional-use approval."
                    ),
                    severity=FindingSeverity.WARNING,
                    confidence=0.91,
                    excerpt=_sentence_containing(text, "conditional") or text[:300],
                )
            )

        setback_match = re.search(r"\b(\d{2,4})\s*[- ]?foot\b.*?setback", lowered)
        if setback_match is None:
            setback_match = re.search(r"setback.*?\b(\d{2,4})\s*[- ]?foot\b", lowered)
        if setback_match is not None:
            value = f"{setback_match.group(1)} feet"
            extracted.append(
                self._requirement(
                    section,
                    category=RequirementCategory.SETBACK,
                    title=f"{value} setback",
                    description=f"The document identifies a {value} setback requirement.",
                    value=value,
                    severity=FindingSeverity.HIGH,
                    confidence=0.90,
                    excerpt=_sentence_containing(text, "setback") or text[:300],
                )
            )

        if "public hearing" in lowered:
            extracted.append(
                self._requirement(
                    section,
                    category=RequirementCategory.PUBLIC_HEARING,
                    title="Public hearing",
                    description="The document requires a public hearing for the approval process.",
                    severity=FindingSeverity.WARNING,
                    confidence=0.88,
                    excerpt=_sentence_containing(text, "public hearing") or text[:300],
                )
            )

        if "decommission" in lowered:
            extracted.append(
                self._requirement(
                    section,
                    category=RequirementCategory.DECOMMISSIONING,
                    title="Decommissioning plan",
                    description="The document requires a decommissioning or removal plan.",
                    severity=FindingSeverity.WARNING,
                    confidence=0.86,
                    excerpt=_sentence_containing(text, "decommission") or text[:300],
                )
            )

        if "financial security" in lowered or "bond" in lowered or "surety" in lowered:
            extracted.append(
                self._requirement(
                    section,
                    category=RequirementCategory.FINANCIAL_SECURITY,
                    title="Financial security",
                    description=(
                        "The document requires financial security such as a bond or surety."
                    ),
                    severity=FindingSeverity.WARNING,
                    confidence=0.84,
                    excerpt=_sentence_containing(text, "financial security")
                    or _sentence_containing(text, "bond")
                    or text[:300],
                )
            )

        if "traffic study" in lowered:
            extracted.append(
                self._requirement(
                    section,
                    category=RequirementCategory.TRAFFIC_STUDY,
                    title="Traffic study",
                    description="The document requires or may require a traffic study.",
                    severity=FindingSeverity.INFO,
                    confidence=0.78,
                    excerpt=_sentence_containing(text, "traffic study") or text[:300],
                )
            )

        if "environmental study" in lowered or "wetland study" in lowered:
            extracted.append(
                self._requirement(
                    section,
                    category=RequirementCategory.ENVIRONMENTAL_STUDY,
                    title="Environmental study",
                    description="The document references an environmental study requirement.",
                    severity=FindingSeverity.INFO,
                    confidence=0.76,
                    excerpt=_sentence_containing(text, "environmental study")
                    or _sentence_containing(text, "wetland study")
                    or text[:300],
                )
            )

        if "application" in lowered and ("site plan" in lowered or "submission" in lowered):
            extracted.append(
                self._requirement(
                    section,
                    category=RequirementCategory.APPLICATION_REQUIREMENT,
                    title="Application materials",
                    description="The document identifies materials required with the application.",
                    severity=FindingSeverity.INFO,
                    confidence=0.82,
                    excerpt=_sentence_containing(text, "application") or text[:300],
                )
            )

        return extracted

    def _requirement(
        self,
        section: RetrievedSection,
        *,
        category: RequirementCategory,
        title: str,
        description: str,
        severity: FindingSeverity,
        confidence: float,
        excerpt: str,
        value: str | None = None,
    ) -> dict[str, Any]:
        return {
            "category": category.value,
            "title": title,
            "description": description,
            "value": value,
            "severity": severity.value,
            "confidence": confidence,
            "requires_human_review": True,
            "evidence": [
                {
                    "document_id": "",
                    "document_name": "",
                    "page_number": section.page_number,
                    "section_name": section.section_heading,
                    "excerpt": excerpt.strip(),
                }
            ],
        }


def parse_extracted_requirements(
    raw_requirements: list[dict[str, Any]],
) -> list[ExtractedRequirement]:
    """Validate model output and coerce unknown categories to ``other``."""
    parsed: list[ExtractedRequirement] = []
    validation_errors: list[str] = []
    for raw in raw_requirements:
        normalized = dict(raw)
        category = str(normalized.get("category", "")).strip()
        if category not in RequirementCategory._value2member_map_:
            normalized["category"] = RequirementCategory.OTHER.value
            normalized["confidence"] = min(float(normalized.get("confidence", 0.0)), 0.55)
        try:
            parsed.append(ExtractedRequirement.model_validate(normalized))
        except (ValidationError, TypeError, ValueError) as exc:
            validation_errors.append(str(exc))

    if validation_errors:
        raise InvalidModelOutputError("Model output did not match the permitting schema.")
    return parsed


def dedupe_requirements(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, int, str]] = set()
    deduped: list[dict[str, Any]] = []
    for requirement in requirements:
        evidence = requirement.get("evidence") or []
        first_evidence = evidence[0] if evidence else {}
        key = (
            str(requirement.get("category")),
            str(requirement.get("title")),
            int(first_evidence.get("page_number") or 0),
            str(first_evidence.get("excerpt")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(requirement)
    return deduped


def _sentence_containing(text: str, needle: str) -> str | None:
    for sentence in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")):
        if needle.lower() in sentence.lower():
            return sentence.strip()
    return None
