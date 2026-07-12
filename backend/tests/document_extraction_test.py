"""Page-aware PDF extraction tests."""

from __future__ import annotations

import json as json_module
from types import TracebackType
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.services.document_extraction import (
    OpenAIRequirementExtractor,
    build_requirement_extractor,
)
from app.services.document_retrieval import RetrievedSection
from app.services.pdf_parser import PdfParser
from tests.document_helpers import fixture_pdf_bytes


def test_parser_extracts_correct_page_count() -> None:
    parsed = PdfParser().parse(
        fixture_pdf_bytes(),
        filename="sample.pdf",
        mime_type="application/pdf",
        max_size_bytes=10_000_000,
    )

    assert parsed.page_count == 3
    assert [page.page_number for page in parsed.pages] == [1, 2, 3]


def test_page_metadata_and_empty_page_are_preserved() -> None:
    parsed = PdfParser().parse(
        fixture_pdf_bytes(),
        filename="sample.pdf",
        mime_type="application/pdf",
        max_size_bytes=10_000_000,
    )

    assert parsed.pages[0].section_heading == "Section 4.3 Solar Energy Systems"
    assert parsed.pages[1].page_number == 2
    assert parsed.pages[1].normalized_text == ""
    assert parsed.pages[2].section_heading == "Section 7.8 Application and Decommissioning"


def test_chunks_never_lose_page_reference() -> None:
    parsed = PdfParser(max_chars=160, overlap_chars=20).parse(
        fixture_pdf_bytes(),
        filename="sample.pdf",
        mime_type="application/pdf",
        max_size_bytes=10_000_000,
    )

    assert parsed.chunks
    assert all(chunk.page_number in {1, 3} for chunk in parsed.chunks)
    assert all(chunk.start_char < chunk.end_char for chunk in parsed.chunks)
    assert all(chunk.section_heading for chunk in parsed.chunks)


def test_auto_extractor_uses_openai_when_key_is_configured() -> None:
    extractor = build_requirement_extractor(
        Settings(openai_api_key="test-key", document_extractor_provider="auto")
    )

    assert isinstance(extractor, OpenAIRequirementExtractor)


def test_openai_extractor_parses_structured_requirements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            return None

        def post(
            self,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, str],
        ) -> httpx.Response:
            assert json["model"] == "gpt-4.1-mini"
            assert headers["Authorization"] == "Bearer test-key"
            content = json_module.dumps(
                {
                    "requirements": [
                        {
                            "category": "setback",
                            "title": "100-foot setback",
                            "description": "A 100-foot setback is required.",
                            "value": "100 feet",
                            "severity": "high",
                            "confidence": 0.88,
                            "requires_human_review": True,
                            "evidence": [
                                {
                                    "document_id": "",
                                    "document_name": "",
                                    "page_number": 2,
                                    "section_name": "Solar ordinance",
                                    "excerpt": (
                                        "Solar facilities shall maintain a 100-foot setback."
                                    ),
                                }
                            ],
                        }
                    ]
                }
            )
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": content}}]},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "Client", FakeClient)
    extractor = OpenAIRequirementExtractor(
        api_key="test-key",
        model="gpt-4.1-mini",
        timeout_seconds=10,
    )

    requirements = extractor.extract(
        [
            RetrievedSection(
                chunk_id="chunk-1",
                page_number=2,
                section_heading="Solar ordinance",
                text="Solar facilities shall maintain a 100-foot setback.",
                score=4,
                matched_terms=["setback"],
            )
        ]
    )

    assert requirements[0]["category"] == "setback"
    assert requirements[0]["evidence"][0]["page_number"] == 2
