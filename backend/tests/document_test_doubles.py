"""Requirement extractor test doubles."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.services.document_errors import TransientAnalysisError
from app.services.document_extraction import FailedCitation
from app.services.document_retrieval import RetrievedSection


class _NoRepair:
    """Doubles that never paraphrase have nothing to repair."""

    def repair(
        self,
        sections: Sequence[RetrievedSection],
        failures: Sequence[FailedCitation],
    ) -> list[dict[str, Any]]:
        return []


class InvalidOutputExtractor(_NoRepair):
    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        return [{"category": "setback", "title": "Missing required fields"}]


class UnknownCategoryExtractor(_NoRepair):
    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        section = sections[0]
        return [
            {
                "category": "mystery_requirement",
                "title": "Unmapped requirement",
                "description": "The model returned a category the API does not know.",
                "value": None,
                "severity": "warning",
                "confidence": 0.93,
                "requires_human_review": True,
                "evidence": [
                    {
                        "document_id": "",
                        "document_name": "",
                        "page_number": section.page_number,
                        "section_name": section.section_heading,
                        "excerpt": section.text.split(".")[0] + ".",
                    }
                ],
            }
        ]


class LowConfidenceExtractor(_NoRepair):
    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        section = sections[0]
        return [
            {
                "category": "public_hearing",
                "title": "Ambiguous hearing requirement",
                "description": "The hearing requirement appears ambiguous.",
                "value": None,
                "severity": "warning",
                "confidence": 0.40,
                "requires_human_review": True,
                "evidence": [
                    {
                        "document_id": "",
                        "document_name": "",
                        "page_number": section.page_number,
                        "section_name": section.section_heading,
                        "excerpt": section.text.split(".")[0] + ".",
                    }
                ],
            }
        ]


class InvalidEvidenceExtractor(_NoRepair):
    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        section = sections[0]
        return [
            {
                "category": "setback",
                "title": "Unsupported setback",
                "description": "This requirement cites text that is not on the page.",
                "value": "999 feet",
                "severity": "high",
                "confidence": 0.91,
                "requires_human_review": True,
                "evidence": [
                    {
                        "document_id": "",
                        "document_name": "",
                        "page_number": section.page_number,
                        "section_name": section.section_heading,
                        "excerpt": "This invented excerpt is not in the PDF.",
                    }
                ],
            }
        ]


class TransientFailureExtractor(_NoRepair):
    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        raise TransientAnalysisError("Model provider timed out.")


class ParaphrasingExtractor(_NoRepair):
    """A model that paraphrases the ordinance instead of quoting it.

    This is the realistic failure of a language model on this task, and the reason
    the repair loop exists. The first pass cites a page correctly but rewrites the
    sentence in its own words, so the citation cannot be verified.
    """

    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        section = sections[0]
        return [
            {
                "category": "public_hearing",
                "title": "Public hearing",
                "description": "A public hearing is required.",
                "value": None,
                "severity": "warning",
                "confidence": 0.92,
                "requires_human_review": True,
                "evidence": [
                    {
                        "document_id": "",
                        "document_name": "",
                        "page_number": section.page_number,
                        "section_name": section.section_heading,
                        # Plausible, on the right page, and nowhere in the document.
                        "excerpt": "The board shall convene a public hearing prior to approval.",
                    }
                ],
            }
        ]


class RepairingExtractor(ParaphrasingExtractor):
    """Paraphrases first, then quotes the source exactly when told to.

    The repair pass copies a real sentence out of the section it was given, which
    is what a well-prompted model does once its bad citation is handed back to it.
    """

    def __init__(self) -> None:
        self.repair_calls = 0
        self.seen_failures: list[FailedCitation] = []

    def repair(
        self,
        sections: Sequence[RetrievedSection],
        failures: Sequence[FailedCitation],
    ) -> list[dict[str, Any]]:
        self.repair_calls += 1
        self.seen_failures.extend(failures)

        section = sections[0]
        verbatim = _sentence_containing(section.text, "hearing") or section.text[:200]
        return [
            {
                "category": "public_hearing",
                "title": "Public hearing",
                "description": "A public hearing is required.",
                "value": None,
                "severity": "warning",
                "confidence": 0.92,
                "requires_human_review": True,
                "evidence": [
                    {
                        "document_id": "",
                        "document_name": "",
                        "page_number": section.page_number,
                        "section_name": section.section_heading,
                        "excerpt": verbatim,
                    }
                ],
            }
        ]


class StubbornlyParaphrasingExtractor(ParaphrasingExtractor):
    """Never produces a real quote, however many times it is asked."""

    def repair(
        self,
        sections: Sequence[RetrievedSection],
        failures: Sequence[FailedCitation],
    ) -> list[dict[str, Any]]:
        return self.extract(sections)


def _sentence_containing(text: str, needle: str) -> str | None:
    import re

    for sentence in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")):
        if needle.lower() in sentence.lower():
            return sentence.strip()
    return None
