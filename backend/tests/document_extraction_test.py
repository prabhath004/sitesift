"""Page-aware PDF extraction tests."""

from __future__ import annotations

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
