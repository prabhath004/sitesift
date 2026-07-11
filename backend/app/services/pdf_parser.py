"""PDF validation, page-aware extraction, and chunking."""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from typing import Any


class PdfValidationError(ValueError):
    """Base class for user-safe PDF validation failures."""


class EmptyPdfError(PdfValidationError):
    """The uploaded file is empty."""


class OversizedPdfError(PdfValidationError):
    """The uploaded file exceeds the configured size limit."""


class InvalidPdfMimeTypeError(PdfValidationError):
    """The uploaded file does not look like a PDF."""


class CorruptPdfError(PdfValidationError):
    """The PDF library could not open or parse the file."""


class PasswordProtectedPdfError(PdfValidationError):
    """The PDF requires a password."""


class EmptyExtractedTextError(PdfValidationError):
    """The PDF opened successfully but contains no extractable text."""


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    raw_text: str
    normalized_text: str
    section_heading: str | None
    char_count: int


@dataclass(frozen=True)
class PageChunk:
    page_number: int
    chunk_index: int
    text: str
    normalized_text: str
    section_heading: str | None
    start_char: int
    end_char: int


@dataclass(frozen=True)
class ParsedPdf:
    page_count: int
    pages: list[ExtractedPage]
    chunks: list[PageChunk]


class PdfParser:
    """Extract page-aware text from PDFs without relying on an LLM."""

    def __init__(self, max_chars: int = 1200, overlap_chars: int = 120) -> None:
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def parse(
        self,
        content: bytes,
        *,
        filename: str,
        mime_type: str,
        max_size_bytes: int,
    ) -> ParsedPdf:
        self._validate_upload(
            content, filename=filename, mime_type=mime_type, max_size=max_size_bytes
        )
        document = self._open_document(content)
        try:
            if bool(getattr(document, "needs_pass", False)):
                raise PasswordProtectedPdfError("Password-protected PDFs are not supported.")

            page_count = int(getattr(document, "page_count", 0))
            if page_count <= 0:
                raise CorruptPdfError("The PDF does not contain any pages.")

            pages = self._extract_pages(document)
        finally:
            close = getattr(document, "close", None)
            if callable(close):
                close()

        if not any(page.normalized_text for page in pages):
            raise EmptyExtractedTextError("No extractable text was found in the PDF.")

        chunks = self.create_chunks(pages)
        return ParsedPdf(page_count=page_count, pages=pages, chunks=chunks)

    def create_chunks(self, pages: list[ExtractedPage]) -> list[PageChunk]:
        chunks: list[PageChunk] = []
        for page in pages:
            if not page.normalized_text:
                continue
            chunks.extend(self._chunk_page(page))
        return chunks

    def _validate_upload(
        self,
        content: bytes,
        *,
        filename: str,
        mime_type: str,
        max_size: int,
    ) -> None:
        if len(content) == 0:
            raise EmptyPdfError("The uploaded PDF is empty.")
        if len(content) > max_size:
            raise OversizedPdfError("The uploaded PDF exceeds the configured size limit.")
        lower_filename = filename.lower()
        if mime_type != "application/pdf" or not lower_filename.endswith(".pdf"):
            raise InvalidPdfMimeTypeError("Only PDF uploads are supported.")
        if not content.startswith(b"%PDF"):
            raise CorruptPdfError("The uploaded file is not a valid PDF.")

    def _open_document(self, content: bytes) -> Any:
        fitz = importlib.import_module("fitz")
        try:
            return fitz.open(stream=content, filetype="pdf")
        except Exception as exc:
            raise CorruptPdfError("The uploaded PDF could not be parsed.") from exc

    def _extract_pages(self, document: Any) -> list[ExtractedPage]:
        pages: list[ExtractedPage] = []
        for index in range(int(document.page_count)):
            page = document.load_page(index)
            raw_text = str(page.get_text("text") or "")
            normalized_text = normalize_text(raw_text)
            pages.append(
                ExtractedPage(
                    page_number=index + 1,
                    raw_text=raw_text,
                    normalized_text=normalized_text,
                    section_heading=detect_section_heading(raw_text),
                    char_count=len(raw_text),
                )
            )
        return pages

    def _chunk_page(self, page: ExtractedPage) -> list[PageChunk]:
        if len(page.normalized_text) <= self.max_chars:
            return [
                PageChunk(
                    page_number=page.page_number,
                    chunk_index=0,
                    text=page.raw_text.strip() or page.normalized_text,
                    normalized_text=page.normalized_text,
                    section_heading=page.section_heading,
                    start_char=0,
                    end_char=len(page.normalized_text),
                )
            ]

        chunks: list[PageChunk] = []
        start = 0
        chunk_index = 0
        while start < len(page.normalized_text):
            end = min(start + self.max_chars, len(page.normalized_text))
            if end < len(page.normalized_text):
                boundary = page.normalized_text.rfind(" ", start, end)
                if boundary > start + self.max_chars // 2:
                    end = boundary

            text = page.normalized_text[start:end].strip()
            if text:
                chunks.append(
                    PageChunk(
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        text=text,
                        normalized_text=text,
                        section_heading=page.section_heading,
                        start_char=start,
                        end_char=end,
                    )
                )
                chunk_index += 1

            if end >= len(page.normalized_text):
                break
            start = max(end - self.overlap_chars, start + 1)
        return chunks


def normalize_text(text: str) -> str:
    """Normalize text for safe matching while preserving semantic content."""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_for_match(text: str) -> str:
    """Case-insensitive normalization for citation verification."""
    normalized = normalize_text(text).lower()
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    normalized = normalized.replace("\u2018", "'").replace("\u2019", "'")
    return normalized


def detect_section_heading(raw_text: str) -> str | None:
    """Return the first ordinance-like heading on the page, if present."""
    for line in raw_text.splitlines():
        clean = normalize_text(line)
        if not clean:
            continue
        if re.match(r"^(section|article|chapter)\s+[\w.\-]+", clean, flags=re.IGNORECASE):
            return clean[:255]
    return None
