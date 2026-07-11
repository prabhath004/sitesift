"""Model-backed requirement extraction.

This module is the only place in SiteSift that calls a language model, and it
lives in ``app/workflows/`` for that reason (CLAUDE.md rule 1: services never call
a model, workflows never compute a score). It produces *claims*; it decides
nothing. Every claim it returns is then checked against the extracted page text by
``app/services/document_evidence.py``, and any claim whose citation cannot be found
verbatim is discarded before it reaches the database.

The model is asked for a strict JSON schema, so its output is parsed by the same
``ExtractedRequirement`` validator the heuristic extractor's output goes through.
It is never trusted to be well-formed, and it is never trusted to be honest about
what the ordinance says.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from app.core.config import Settings
from app.services.document_errors import InvalidModelOutputError, TransientAnalysisError
from app.services.document_extraction import (
    FailedCitation,
    HeuristicRequirementExtractor,
    RequirementExtractor,
)
from app.services.document_retrieval import RetrievedSection

SYSTEM_PROMPT = """\
You extract permitting requirements from zoning and permitting ordinances for a \
renewable-energy site-screening tool. A developer will act on what you return, so \
a wrong or invented requirement is worse than a missing one.

Rules:
1. Only report a requirement that the supplied text actually states. If the text \
does not state it, do not report it.
2. Every requirement must cite the page it came from and quote the source text \
EXACTLY — character for character, copied from the section you were given. Do not \
paraphrase, summarise, correct, reflow, or tidy the quote. A quote that is not a \
verbatim substring of the page will be rejected and the requirement discarded.
3. Quote enough to stand alone (a full sentence or clause), but nothing beyond \
what supports the requirement.
4. Use the page_number of the section the quote came from. Do not guess a page.
5. confidence is how certain you are that the text states this requirement: 0.9+ \
when it is stated plainly, 0.5-0.7 when it is implied or conditional, below 0.5 \
when the text is ambiguous.
6. severity: `high` for a requirement that could block or materially delay the \
project (setbacks, prohibitions, discretionary approvals), `warning` for a real \
obligation with a normal path (hearings, decommissioning plans, bonds), `info` for \
a procedural or informational item.

Return an empty list if the text states no permitting requirements."""

REPAIR_PROMPT = """\
Some of your citations were rejected: the quoted text was NOT found on the page you \
named. You paraphrased or altered the source instead of copying it.

Re-extract ONLY those requirements. For each one, copy the supporting sentence from \
the section text below character for character — including its punctuation, casing, \
spacing, and any awkward line wrapping. Do not improve the wording. If you cannot \
find text on that page that actually states the requirement, omit the requirement \
entirely rather than inventing a quote."""


def _requirement_schema() -> dict[str, Any]:
    """The JSON schema the model must fill. Mirrors ``ExtractedRequirement``."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["requirements"],
        "properties": {
            "requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "category",
                        "title",
                        "description",
                        "value",
                        "severity",
                        "confidence",
                        "evidence",
                    ],
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": [
                                "use_permission",
                                "setback",
                                "public_hearing",
                                "decommissioning",
                                "financial_security",
                                "environmental_study",
                                "traffic_study",
                                "application_requirement",
                                "other",
                            ],
                        },
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "value": {
                            "type": ["string", "null"],
                            "description": "The specific figure, e.g. '100 feet'. Null if none.",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["info", "warning", "high", "fatal"],
                        },
                        "confidence": {"type": "number"},
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["page_number", "section_name", "excerpt"],
                                "properties": {
                                    "page_number": {"type": "integer"},
                                    "section_name": {"type": ["string", "null"]},
                                    "excerpt": {
                                        "type": "string",
                                        "description": "Verbatim substring of the page text.",
                                    },
                                },
                            },
                        },
                    },
                },
            }
        },
    }


class OpenAIRequirementExtractor:
    """Extracts permitting requirements with an OpenAI model, in strict JSON.

    ``client`` is injectable so the tests can drive this class without a network
    call or an API key.
    """

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client or self._build_client(settings)
        self._model = settings.extraction_model

    @staticmethod
    def _build_client(settings: Settings) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise TransientAnalysisError("The OpenAI client is not installed.") from exc

        return OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.extraction_timeout_seconds,
        )

    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        if not sections:
            return []
        return self._call(SYSTEM_PROMPT, self._sections_message(sections))

    def repair(
        self,
        sections: Sequence[RetrievedSection],
        failures: Sequence[FailedCitation],
    ) -> list[dict[str, Any]]:
        if not sections or not failures:
            return []

        rejected = "\n".join(
            f"- {failure.title!r} cited page {failure.page_number} with: "
            f"{failure.excerpt!r} — {failure.reason}"
            for failure in failures
        )
        message = (
            f"{REPAIR_PROMPT}\n\nRejected citations:\n{rejected}\n\n"
            f"{self._sections_message(sections)}"
        )
        return self._call(SYSTEM_PROMPT, message)

    def _call(self, system_prompt: str, user_message: str) -> list[dict[str, Any]]:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "permitting_requirements",
                        "strict": True,
                        "schema": _requirement_schema(),
                    },
                },
                temperature=0,
            )
        except Exception as exc:
            # The provider is down, rate-limiting, or unreachable. That is a
            # transient failure of *this* step, not a screening failure: the
            # deterministic results stay untouched (CLAUDE.md rule 4).
            raise TransientAnalysisError(
                "The extraction model could not be reached. Deterministic screening "
                "results are unaffected."
            ) from exc

        return self._parse(response)

    def _parse(self, response: Any) -> list[dict[str, Any]]:
        try:
            content = response.choices[0].message.content
            payload = json.loads(content or "{}")
            requirements = payload["requirements"]
        except (AttributeError, IndexError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise InvalidModelOutputError(
                "The extraction model did not return the permitting schema."
            ) from exc

        if not isinstance(requirements, list):
            raise InvalidModelOutputError(
                "The extraction model did not return a list of requirements."
            )

        # `requires_human_review` is not the model's to decide. It is forced true
        # here and again by the schema validator: a document-derived requirement is
        # never final until a person approves it (spec §9.3).
        for requirement in requirements:
            if isinstance(requirement, dict):
                requirement["requires_human_review"] = True
                requirement.setdefault("evidence", [])
                for evidence in requirement["evidence"]:
                    if isinstance(evidence, dict):
                        # Filled in by evidence validation from the real document.
                        evidence.setdefault("document_id", "")
                        evidence.setdefault("document_name", "")

        return [item for item in requirements if isinstance(item, dict)]

    @staticmethod
    def _sections_message(sections: Sequence[RetrievedSection]) -> str:
        """The retrieved ordinance sections, each tagged with the page it is on.

        The page tag is what makes a citation checkable: the model can only cite a
        page it was shown, and the excerpt is later matched against that page's
        extracted text.
        """
        blocks = []
        for section in sections:
            heading = section.section_heading or "(no heading)"
            blocks.append(f"--- page {section.page_number} | {heading} ---\n{section.text}")
        return (
            "Extract the permitting requirements stated in these ordinance sections. "
            "Quote exactly from the text between the markers.\n\n" + "\n\n".join(blocks)
        )


def select_extractor(settings: Settings) -> RequirementExtractor:
    """The model-backed extractor when a key is configured, the heuristic otherwise.

    The fallback is deliberate, and it is not a lesser mode of the product: it is
    what lets the app run, the tests pass, and a demo survive a dead network with no
    API key present. The system degrades to *deterministic*, never to *fabricated*.
    """
    if settings.openai_api_key:
        return OpenAIRequirementExtractor(settings)
    return HeuristicRequirementExtractor()
