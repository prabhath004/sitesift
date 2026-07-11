"""Model-backed extraction: the citation-repair loop, and the OpenAI extractor.

No test here touches the network. The extractor is injected, and the OpenAI client
is stubbed — a test suite that needs an API key is a test suite that does not run.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document_workflow import DocumentWorkflowEvent
from app.models.risk_finding import RiskFinding
from app.services.document_errors import InvalidModelOutputError, TransientAnalysisError
from app.services.document_extraction import FailedCitation, HeuristicRequirementExtractor
from app.services.document_retrieval import RetrievedSection
from app.services.document_service import upload_document
from app.workflows.llm_extraction import OpenAIRequirementExtractor, select_extractor
from app.workflows.permitting_graph import analyze_document
from tests.document_helpers import create_site, fixture_pdf_bytes
from tests.document_test_doubles import (
    ParaphrasingExtractor,
    RepairingExtractor,
    StubbornlyParaphrasingExtractor,
)


def _settings(**overrides: Any) -> Settings:
    base = Settings(
        document_storage_dir="/tmp/sitesift-test-documents",
        extraction_citation_retries=1,
    )
    return base.model_copy(update=overrides)


def _upload(db: Session, settings: Settings) -> Any:
    site = create_site(db)
    return upload_document(
        db,
        site_id=site.id,
        filename="sample.pdf",
        mime_type="application/pdf",
        content=fixture_pdf_bytes(),
        settings=settings,
    ).document


def _sections() -> list[RetrievedSection]:
    return [
        RetrievedSection(
            chunk_id="chunk-1",
            page_number=2,
            section_heading="Section 4.3",
            text="A public hearing shall be held before the Planning Board grants approval.",
            score=6,
            matched_terms=["hearing"],
        )
    ]


# --- the repair loop -------------------------------------------------------


def test_paraphrased_citation_is_repaired_and_then_persisted(db: Session) -> None:
    """The model rewrites the ordinance; the graph makes it quote instead."""
    settings = _settings()
    document = _upload(db, settings)
    extractor = RepairingExtractor()

    response = analyze_document(
        db,
        document_id=document.id,
        settings=settings,
        idempotency_key="repair-success",
        extractor=extractor,
    )

    assert extractor.repair_calls == 1
    # The model was shown its own bad citation, not just asked to try again.
    assert extractor.seen_failures[0].excerpt.startswith("The board shall convene")
    assert "not found" in extractor.seen_failures[0].reason

    # The requirement survived — with a quote that is really in the document.
    assert len(response.findings) == 1
    finding = response.findings[0]
    assert finding.title == "Public hearing"
    excerpt = finding.evidence[0].excerpt
    page = next(p for p in document.pages if p.page_number == finding.evidence[0].page_number)
    assert excerpt in page.raw_text


def test_paraphrased_citation_that_cannot_be_repaired_is_never_persisted(db: Session) -> None:
    """A claim the model will not substantiate is dropped, not shown."""
    settings = _settings()
    document = _upload(db, settings)

    response = analyze_document(
        db,
        document_id=document.id,
        settings=settings,
        idempotency_key="repair-failure",
        extractor=StubbornlyParaphrasingExtractor(),
    )

    assert response.findings == []
    assert db.query(RiskFinding).count() == 0
    assert response.document.processing_status.value == "partially_completed"
    # The run says why, rather than quietly showing fewer findings.
    assert "could not be verified" in (response.document.error_message or "")


def test_repair_is_bounded_by_the_configured_budget(db: Session) -> None:
    """The loop cannot spin: one retry configured, one repair attempt made."""
    settings = _settings(extraction_citation_retries=1)
    document = _upload(db, settings)

    analyze_document(
        db,
        document_id=document.id,
        settings=settings,
        idempotency_key="repair-bounded",
        extractor=StubbornlyParaphrasingExtractor(),
    )

    repairs = (
        db.query(DocumentWorkflowEvent)
        .filter(
            DocumentWorkflowEvent.document_id == document.id,
            DocumentWorkflowEvent.node_name == "repair_citations",
            DocumentWorkflowEvent.status == "completed",
        )
        .count()
    )
    assert repairs == 1


def test_repair_can_be_disabled(db: Session) -> None:
    settings = _settings(extraction_citation_retries=0)
    document = _upload(db, settings)

    response = analyze_document(
        db,
        document_id=document.id,
        settings=settings,
        idempotency_key="repair-disabled",
        extractor=ParaphrasingExtractor(),
    )

    assert response.findings == []
    repairs = (
        db.query(DocumentWorkflowEvent)
        .filter(DocumentWorkflowEvent.node_name == "repair_citations")
        .count()
    )
    assert repairs == 0


def test_repair_appears_in_the_public_workflow_trail(db: Session) -> None:
    """The reviewer can see that a citation was rejected and re-requested."""
    settings = _settings()
    document = _upload(db, settings)

    response = analyze_document(
        db,
        document_id=document.id,
        settings=settings,
        idempotency_key="repair-trail",
        extractor=RepairingExtractor(),
    )

    repair_events = [e for e in response.workflow_events if e.node_name == "repair_citations"]
    assert repair_events, "the repair step must be visible in the workflow trail"

    completed = next(e for e in repair_events if e.status.value == "completed")
    assert completed.output_summary["repaired_requirement_count"] == 1
    # Summaries only — no document text, no model reasoning (CLAUDE.md rules 6, 7).
    assert "excerpt" not in json.dumps(completed.output_summary)


# --- extractor selection ---------------------------------------------------


def test_no_api_key_falls_back_to_the_deterministic_extractor() -> None:
    """The app runs, and the tests pass, with no key configured."""
    extractor = select_extractor(_settings(openai_api_key=None))
    assert isinstance(extractor, HeuristicRequirementExtractor)


def test_an_api_key_selects_the_model_backed_extractor() -> None:
    extractor = select_extractor(_settings(openai_api_key="sk-test-not-a-real-key"))
    assert isinstance(extractor, OpenAIRequirementExtractor)


# --- the OpenAI extractor, with a stubbed client ---------------------------


class _StubResponse:
    def __init__(self, content: str) -> None:
        message = type("Message", (), {"content": content})
        choice = type("Choice", (), {"message": message})
        self.choices = [choice]


class _StubClient:
    """Records the request and returns a canned completion."""

    def __init__(self, content: str = "", error: Exception | None = None) -> None:
        self._content = content
        self._error = error
        self.calls: list[dict[str, Any]] = []
        self.chat = type("Chat", (), {"completions": self})()

    def create(self, **kwargs: Any) -> _StubResponse:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return _StubResponse(self._content)


def _extractor(client: _StubClient) -> OpenAIRequirementExtractor:
    return OpenAIRequirementExtractor(_settings(openai_api_key="sk-test"), client=client)


def test_openai_extractor_sends_page_tagged_sections_and_a_strict_schema() -> None:
    client = _StubClient(json.dumps({"requirements": []}))
    _extractor(client).extract(_sections())

    request = client.calls[0]
    assert request["model"] == "gpt-4.1-mini"
    assert request["temperature"] == 0
    assert request["response_format"]["json_schema"]["strict"] is True

    prompt = request["messages"][1]["content"]
    # The model can only cite a page it was shown — that is what makes the
    # citation checkable at all.
    assert "--- page 2 | Section 4.3 ---" in prompt
    assert "A public hearing shall be held" in prompt
    assert "EXACTLY" in request["messages"][0]["content"]


def test_openai_extractor_parses_structured_output_and_forces_human_review() -> None:
    client = _StubClient(
        json.dumps(
            {
                "requirements": [
                    {
                        "category": "public_hearing",
                        "title": "Public hearing",
                        "description": "A hearing is required.",
                        "value": None,
                        "severity": "warning",
                        "confidence": 0.9,
                        # The model claims it may skip review. It may not.
                        "requires_human_review": False,
                        "evidence": [
                            {
                                "page_number": 2,
                                "section_name": "Section 4.3",
                                "excerpt": "A public hearing shall be held.",
                            }
                        ],
                    }
                ]
            }
        )
    )

    requirements = _extractor(client).extract(_sections())

    assert len(requirements) == 1
    assert requirements[0]["requires_human_review"] is True
    assert requirements[0]["evidence"][0]["page_number"] == 2


def test_openai_extractor_rejects_output_that_is_not_the_schema() -> None:
    client = _StubClient("not json at all")
    with pytest.raises(InvalidModelOutputError):
        _extractor(client).extract(_sections())


def test_provider_failure_is_transient_and_does_not_claim_a_screening_failure() -> None:
    client = _StubClient(error=RuntimeError("connection reset"))
    with pytest.raises(TransientAnalysisError) as caught:
        _extractor(client).extract(_sections())

    assert "Deterministic screening results are unaffected" in str(caught.value)


def test_repair_prompt_shows_the_model_its_rejected_citation() -> None:
    client = _StubClient(json.dumps({"requirements": []}))
    failures = [
        FailedCitation(
            title="Public hearing",
            page_number=2,
            excerpt="The board shall convene a public hearing prior to approval.",
            reason="cites text that was not found on page 2",
        )
    ]

    _extractor(client).repair(_sections(), failures)

    prompt = client.calls[0]["messages"][1]["content"]
    assert "were rejected" in prompt
    assert "The board shall convene a public hearing prior to approval." in prompt
    assert "character for character" in prompt


def test_extract_with_no_sections_makes_no_model_call() -> None:
    client = _StubClient(json.dumps({"requirements": []}))
    assert _extractor(client).extract([]) == []
    assert client.calls == []
