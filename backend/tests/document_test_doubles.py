"""Requirement extractor test doubles."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.services.document_errors import TransientAnalysisError
from app.services.document_retrieval import RetrievedSection


class InvalidOutputExtractor:
    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        return [{"category": "setback", "title": "Missing required fields"}]


class UnknownCategoryExtractor:
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


class LowConfidenceExtractor:
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


class InvalidEvidenceExtractor:
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


class TransientFailureExtractor:
    def extract(self, sections: Sequence[RetrievedSection]) -> list[dict[str, Any]]:
        raise TransientAnalysisError("Model provider timed out.")
