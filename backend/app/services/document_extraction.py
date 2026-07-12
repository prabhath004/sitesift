"""Requirement extraction interfaces and model-backed/local extractors."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any, Protocol

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.common import FindingSeverity
from app.schemas.document import ExtractedRequirement
from app.schemas.finding import RequirementCategory
from app.services.document_errors import InvalidModelOutputError, TransientAnalysisError
from app.services.document_retrieval import RetrievedSection

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"

_SYSTEM_PROMPT = """You extract permitting and zoning requirements for power-project diligence.

Use only the supplied document sections. Return no requirement unless a provided
section contains exact supporting text. Every evidence excerpt must be copied
verbatim from the section text and must support the requirement. Do not summarize
or invent citations.

Category guidance:
- use_permission: conditional-use, special-use, permitted-use, board approval, or zoning approval.
- setback: numeric or specific distance/height/property-line constraints.
- public_hearing: hearing, notice, public meeting, or board hearing requirements.
- decommissioning: decommissioning, removal, restoration, abandonment requirements.
- financial_security: bond, surety, escrow, letter of credit, financial guarantee.
- environmental_study: wetland, environmental, habitat, stormwater, or similar studies.
- traffic_study: traffic, road, access, driveway, haul-route studies.
- application_requirement: site plan, drawings, application materials, submission contents.
- other: relevant permitting requirement that does not fit the categories above.

Severity guidance:
- info: procedural or informational obligation.
- warning: review, study, hearing, approval, or documentation burden.
- high: hard constraint likely to materially affect layout, cost, or schedule.
- fatal: explicit prohibition or clear impossibility only.

Set requires_human_review to true for every requirement. If the sections do not
contain any supportable permitting requirements, return an empty requirements array.
"""


class RequirementExtractor(Protocol):
    """Interface for LLM-backed or mocked requirement extractors."""

    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        """Return raw structured requirements."""


def build_requirement_extractor(settings: Settings) -> RequirementExtractor:
    """Choose the configured extraction provider.

    ``auto`` is the normal product mode: use OpenAI when ``OPENAI_API_KEY`` is
    configured, otherwise keep the app runnable with the deterministic local
    extractor. Tests set ``document_extractor_provider=heuristic`` so they never
    call the network through a developer's real ``.env`` file.
    """
    provider = settings.document_extractor_provider.strip().lower()
    if provider == "heuristic":
        return HeuristicRequirementExtractor()
    if provider == "openai":
        if not settings.openai_api_key:
            raise TransientAnalysisError(
                "OpenAI document extraction is configured, but OPENAI_API_KEY is missing."
            )
        return OpenAIRequirementExtractor(
            api_key=settings.openai_api_key,
            model=settings.openai_document_model,
            timeout_seconds=settings.openai_request_timeout_seconds,
        )
    if provider == "auto":
        if settings.openai_api_key:
            return OpenAIRequirementExtractor(
                api_key=settings.openai_api_key,
                model=settings.openai_document_model,
                timeout_seconds=settings.openai_request_timeout_seconds,
            )
        return HeuristicRequirementExtractor()
    raise InvalidModelOutputError(
        "DOCUMENT_EXTRACTOR_PROVIDER must be one of: auto, openai, heuristic."
    )


class OpenAIRequirementExtractor:
    """Extract requirements with OpenAI structured outputs."""

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        if not sections:
            return []

        payload = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _sections_prompt(sections)},
            ],
            "response_format": _response_format_schema(),
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(OPENAI_CHAT_COMPLETIONS_URL, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise TransientAnalysisError("OpenAI requirement extraction timed out.") from exc
        except httpx.HTTPError as exc:
            raise TransientAnalysisError("OpenAI requirement extraction failed.") from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise TransientAnalysisError(
                "OpenAI requirement extraction is temporarily unavailable."
            )
        if response.status_code >= 400:
            raise InvalidModelOutputError("OpenAI requirement extraction request was rejected.")

        return dedupe_requirements(_requirements_from_response(response))


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


def _sections_prompt(sections: Sequence[RetrievedSection]) -> str:
    lines = [
        "Extract permitting requirements from these retrieved zoning/permitting sections.",
        "Use the page number from each section in citations.",
    ]
    for index, section in enumerate(sections, start=1):
        heading = section.section_heading or "Untitled section"
        matched_terms = ", ".join(section.matched_terms) if section.matched_terms else "none"
        lines.extend(
            [
                "",
                f"SECTION {index}",
                f"page_number: {section.page_number}",
                f"section_heading: {heading}",
                f"matched_terms: {matched_terms}",
                "text:",
                section.text,
            ]
        )
    return "\n".join(lines)


def _response_format_schema() -> dict[str, Any]:
    requirement_categories = [category.value for category in RequirementCategory]
    severities = [severity.value for severity in FindingSeverity]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "permitting_requirements",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "requirements": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "category": {"type": "string", "enum": requirement_categories},
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "value": {"type": ["string", "null"]},
                                "severity": {"type": "string", "enum": severities},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "requires_human_review": {"type": "boolean"},
                                "evidence": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "document_id": {"type": "string"},
                                            "document_name": {"type": "string"},
                                            "page_number": {"type": "integer", "minimum": 1},
                                            "section_name": {"type": ["string", "null"]},
                                            "excerpt": {"type": "string"},
                                        },
                                        "required": [
                                            "document_id",
                                            "document_name",
                                            "page_number",
                                            "section_name",
                                            "excerpt",
                                        ],
                                    },
                                },
                            },
                            "required": [
                                "category",
                                "title",
                                "description",
                                "value",
                                "severity",
                                "confidence",
                                "requires_human_review",
                                "evidence",
                            ],
                        },
                    }
                },
                "required": ["requirements"],
            },
        },
    }


def _requirements_from_response(response: httpx.Response) -> list[dict[str, Any]]:
    body: Any = response.json()
    if not isinstance(body, dict):
        raise InvalidModelOutputError("OpenAI returned an unexpected response.")

    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise InvalidModelOutputError("OpenAI returned no extraction choices.")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise InvalidModelOutputError("OpenAI returned an invalid extraction choice.")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise InvalidModelOutputError("OpenAI returned an invalid extraction message.")
    if message.get("refusal"):
        raise InvalidModelOutputError("OpenAI refused to extract permitting requirements.")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise InvalidModelOutputError("OpenAI returned an empty extraction response.")

    try:
        parsed: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise InvalidModelOutputError("OpenAI returned invalid extraction JSON.") from exc

    if not isinstance(parsed, dict):
        raise InvalidModelOutputError("OpenAI extraction JSON must be an object.")
    requirements = parsed.get("requirements")
    if not isinstance(requirements, list):
        raise InvalidModelOutputError("OpenAI extraction JSON must include requirements.")
    if not all(isinstance(requirement, dict) for requirement in requirements):
        raise InvalidModelOutputError("OpenAI requirements must be objects.")
    return requirements


def _sentence_containing(text: str, needle: str) -> str | None:
    for sentence in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")):
        if needle.lower() in sentence.lower():
            return sentence.strip()
    return None
