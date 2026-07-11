"""LangGraph workflow for permitting-document analysis."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.models.candidate_site import CandidateSite
from app.models.document import Document, DocumentChunk
from app.models.document_workflow import DocumentAnalysisRequest, DocumentWorkflowEvent
from app.schemas.common import DocumentProcessingStatus, ReviewStatus
from app.schemas.document import DocumentAnalysisResponse, ExtractedRequirement
from app.schemas.evidence import EvidenceCreate
from app.services.document_confidence import assign_confidence
from app.services.document_errors import NotFoundError, safe_error_message
from app.services.document_evidence import validate_requirement_evidence
from app.services.document_extraction import (
    HeuristicRequirementExtractor,
    RequirementExtractor,
    parse_extracted_requirements,
)
from app.services.document_retrieval import RetrievedSection, retrieve_relevant_sections
from app.services.document_service import (
    PersistableRequirement,
    build_analysis_response,
    get_document_with_text,
    persist_document_findings,
    persist_extracted_text,
    update_document_status,
)
from app.services.pdf_parser import PdfParser
from app.services.pdf_storage import read_pdf


class AnalysisState(TypedDict):
    project_id: str
    site_id: str
    document_id: str
    analysis_request_id: str
    project_type: NotRequired[str]
    page_count: NotRequired[int]
    page_summaries: NotRequired[list[dict[str, Any]]]
    page_chunks: NotRequired[list[dict[str, Any]]]
    relevant_sections: NotRequired[list[dict[str, Any]]]
    extracted_requirements: NotRequired[list[dict[str, Any]]]
    valid_requirements: NotRequired[list[dict[str, Any]]]
    final_findings: NotRequired[list[dict[str, Any]]]
    persisted_finding_count: NotRequired[int]
    validation_errors: NotRequired[list[str]]
    status: str
    summary: NotRequired[str]


NodeFunction = Callable[[AnalysisState], dict[str, Any]]


def analyze_document(
    db: Session,
    *,
    document_id: str,
    settings: Settings,
    idempotency_key: str | None,
    extractor: RequirementExtractor | None = None,
) -> DocumentAnalysisResponse:
    """Run the permitting-document graph synchronously."""
    document = get_document_with_text(db, document_id)
    request = _get_or_create_request(db, document=document, idempotency_key=idempotency_key)

    if (
        _is_terminal(request.status)
        and document.processing_status != DocumentProcessingStatus.FAILED.value
    ):
        return build_analysis_response(db, document.id)

    if request.status == DocumentProcessingStatus.FAILED.value:
        request.retry_count += 1

    request.status = DocumentProcessingStatus.ANALYZING.value
    request.error_message = None
    db.add(request)
    db.commit()

    graph = _build_graph(
        db=db, settings=settings, extractor=extractor or HeuristicRequirementExtractor()
    )
    initial_state: AnalysisState = {
        "project_id": document.project_id,
        "site_id": document.site_id,
        "document_id": document.id,
        "analysis_request_id": request.id,
        "status": DocumentProcessingStatus.ANALYZING.value,
        "validation_errors": [],
    }

    try:
        final_state = graph.invoke(initial_state)
        final_status = DocumentProcessingStatus(final_state["status"])
        request.status = final_status.value
        request.completed_at = request.completed_at or document.updated_at
        request.error_message = None
        db.add(request)
        db.commit()
    except Exception as exc:
        message = safe_error_message(exc)
        document = get_document_with_text(db, document_id)
        update_document_status(db, document, DocumentProcessingStatus.FAILED, error_message=message)
        request.status = DocumentProcessingStatus.FAILED.value
        request.error_message = message
        db.add(request)
        db.commit()

    return build_analysis_response(db, document_id)


def _build_graph(
    *,
    db: Session,
    settings: Settings,
    extractor: RequirementExtractor,
) -> Any:
    graph: Any = StateGraph(AnalysisState)
    graph.add_node("validate_document", _evented(db, "validate_document", _validate_document(db)))
    graph.add_node("extract_text", _evented(db, "extract_text", _extract_text(db, settings)))
    graph.add_node(
        "create_page_chunks", _evented(db, "create_page_chunks", _create_page_chunks(db))
    )
    graph.add_node(
        "retrieve_relevant_sections",
        _evented(db, "retrieve_relevant_sections", _retrieve_sections(db)),
    )
    graph.add_node(
        "extract_requirements",
        _evented(db, "extract_requirements", _extract_requirements(extractor)),
    )
    graph.add_node("validate_evidence", _evented(db, "validate_evidence", _validate_evidence(db)))
    graph.add_node("flag_ambiguity", _evented(db, "flag_ambiguity", _flag_ambiguity()))
    graph.add_node("persist_findings", _evented(db, "persist_findings", _persist_findings(db)))
    graph.add_node("generate_summary", _evented(db, "generate_summary", _generate_summary()))

    graph.add_edge(START, "validate_document")
    graph.add_edge("validate_document", "extract_text")
    graph.add_edge("extract_text", "create_page_chunks")
    graph.add_edge("create_page_chunks", "retrieve_relevant_sections")
    graph.add_edge("retrieve_relevant_sections", "extract_requirements")
    graph.add_edge("extract_requirements", "validate_evidence")
    graph.add_edge("validate_evidence", "flag_ambiguity")
    graph.add_edge("flag_ambiguity", "persist_findings")
    graph.add_edge("persist_findings", "generate_summary")
    graph.add_edge("generate_summary", END)
    return graph.compile()


def _validate_document(db: Session) -> NodeFunction:
    def node(state: AnalysisState) -> dict[str, Any]:
        document = get_document_with_text(db, state["document_id"])
        site = db.scalar(
            select(CandidateSite)
            .where(CandidateSite.id == document.site_id)
            .options(selectinload(CandidateSite.project))
        )
        if site is None:
            raise NotFoundError("Site was not found.")
        update_document_status(db, document, DocumentProcessingStatus.VALIDATING)
        return {
            "project_id": document.project_id,
            "site_id": document.site_id,
            "project_type": site.project.project_type,
            "page_count": document.page_count,
            "status": DocumentProcessingStatus.VALIDATING.value,
        }

    return node


def _extract_text(db: Session, settings: Settings) -> NodeFunction:
    def node(state: AnalysisState) -> dict[str, Any]:
        document = get_document_with_text(db, state["document_id"])
        update_document_status(db, document, DocumentProcessingStatus.EXTRACTING)
        if not document.pages:
            parser = PdfParser(
                max_chars=settings.document_chunk_max_chars,
                overlap_chars=settings.document_chunk_overlap_chars,
            )
            parsed = parser.parse(
                read_pdf(document.storage_path),
                filename=document.filename,
                mime_type=document.mime_type,
                max_size_bytes=settings.document_max_upload_bytes,
            )
            persist_extracted_text(db, document=document, parsed=parsed)
            db.flush()
            document = get_document_with_text(db, document.id)

        page_summaries = [
            {
                "page_number": page.page_number,
                "char_count": page.char_count,
                "has_text": bool(page.normalized_text),
                "section_heading": page.section_heading,
            }
            for page in document.pages
        ]
        return {
            "page_count": document.page_count,
            "status": DocumentProcessingStatus.EXTRACTING.value,
            "validation_errors": state.get("validation_errors", []),
            "page_chunks": state.get("page_chunks", []),
            "page_summaries": page_summaries,
        }

    return node


def _create_page_chunks(db: Session) -> NodeFunction:
    def node(state: AnalysisState) -> dict[str, Any]:
        document = get_document_with_text(db, state["document_id"])
        chunk_summaries = [
            _chunk_to_state(chunk)
            for chunk in sorted(
                document.chunks, key=lambda item: (item.page_number, item.chunk_index)
            )
        ]
        return {
            "page_chunks": chunk_summaries,
            "status": DocumentProcessingStatus.EXTRACTING.value,
        }

    return node


def _retrieve_sections(db: Session) -> NodeFunction:
    def node(state: AnalysisState) -> dict[str, Any]:
        document = get_document_with_text(db, state["document_id"])
        update_document_status(db, document, DocumentProcessingStatus.RETRIEVING)
        chunks = list(
            db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document.id)
                .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
            ).all()
        )
        sections = retrieve_relevant_sections(
            chunks, project_type=state.get("project_type", "other")
        )
        validation_errors = list(state.get("validation_errors", []))
        if not sections:
            validation_errors.append("No relevant permitting sections were found.")
        return {
            "relevant_sections": [_section_to_state(section) for section in sections],
            "validation_errors": validation_errors,
            "status": DocumentProcessingStatus.RETRIEVING.value,
        }

    return node


def _extract_requirements(extractor: RequirementExtractor) -> NodeFunction:
    def node(state: AnalysisState) -> dict[str, Any]:
        sections = [_state_to_section(section) for section in state.get("relevant_sections", [])]
        if not sections:
            return {
                "extracted_requirements": [],
                "status": DocumentProcessingStatus.ANALYZING.value,
            }
        raw_requirements = extractor.extract(sections)
        requirements = parse_extracted_requirements(raw_requirements)
        return {
            "extracted_requirements": [
                requirement.model_dump(mode="json") for requirement in requirements
            ],
            "status": DocumentProcessingStatus.ANALYZING.value,
        }

    return node


def _validate_evidence(db: Session) -> NodeFunction:
    def node(state: AnalysisState) -> dict[str, Any]:
        document = get_document_with_text(db, state["document_id"])
        valid_requirements: list[dict[str, Any]] = []
        validation_errors = list(state.get("validation_errors", []))

        for raw_requirement in state.get("extracted_requirements", []):
            requirement = ExtractedRequirement.model_validate(raw_requirement)
            result = validate_requirement_evidence(document, document.pages, requirement)
            validation_errors.extend(result.errors)
            if result.evidence:
                valid_requirements.append(
                    {
                        "requirement": requirement.model_dump(mode="json"),
                        "evidence": [
                            evidence.model_dump(mode="json") for evidence in result.evidence
                        ],
                    }
                )

        return {
            "valid_requirements": valid_requirements,
            "validation_errors": validation_errors,
            "status": DocumentProcessingStatus.ANALYZING.value,
        }

    return node


def _flag_ambiguity() -> NodeFunction:
    def node(state: AnalysisState) -> dict[str, Any]:
        final_requirements: list[dict[str, Any]] = []
        validation_errors = list(state.get("validation_errors", []))
        workflow_status = DocumentProcessingStatus.NEEDS_REVIEW

        for item in state.get("valid_requirements", []):
            requirement = ExtractedRequirement.model_validate(item["requirement"])
            decision = assign_confidence(requirement)
            if decision.workflow_status == DocumentProcessingStatus.PARTIALLY_COMPLETED:
                workflow_status = DocumentProcessingStatus.PARTIALLY_COMPLETED
            if not decision.keep_requirement:
                validation_errors.append(
                    f"Requirement '{requirement.title}' was rejected because "
                    "confidence was too low."
                )
                continue
            final_requirements.append(
                {
                    "requirement": requirement.model_dump(mode="json"),
                    "evidence": item["evidence"],
                    "review_status": decision.review_status.value,
                    "requires_human_review": decision.requires_human_review,
                }
            )

        if validation_errors and workflow_status != DocumentProcessingStatus.PARTIALLY_COMPLETED:
            workflow_status = DocumentProcessingStatus.PARTIALLY_COMPLETED
        return {
            "final_findings": final_requirements,
            "validation_errors": validation_errors,
            "status": workflow_status.value,
        }

    return node


def _persist_findings(db: Session) -> NodeFunction:
    def node(state: AnalysisState) -> dict[str, Any]:
        document = get_document_with_text(db, state["document_id"])
        persistable: list[PersistableRequirement] = []
        for item in state.get("final_findings", []):
            persistable.append(
                PersistableRequirement(
                    requirement=ExtractedRequirement.model_validate(item["requirement"]),
                    evidence=[
                        EvidenceCreate.model_validate(evidence) for evidence in item["evidence"]
                    ],
                    review_status=ReviewStatus(item["review_status"]),
                    requires_human_review=bool(item["requires_human_review"]),
                )
            )

        findings = persist_document_findings(db, document=document, requirements=persistable)
        status = DocumentProcessingStatus(state["status"])
        if not persistable and status != DocumentProcessingStatus.FAILED:
            status = DocumentProcessingStatus.PARTIALLY_COMPLETED
        update_document_status(
            db,
            document,
            status,
            error_message="; ".join(state.get("validation_errors", [])) or None,
        )
        db.flush()
        return {
            "persisted_finding_count": len(findings),
            "status": status.value,
        }

    return node


def _generate_summary() -> NodeFunction:
    def node(state: AnalysisState) -> dict[str, Any]:
        finding_count = len(state.get("final_findings", []))
        validation_count = len(state.get("validation_errors", []))
        if finding_count == 0:
            summary = "No verified requirements were found."
        else:
            summary = f"{finding_count} requirement(s) require human review."
        if validation_count:
            summary = f"{summary} {validation_count} validation issue(s) were recorded."
        return {"summary": summary, "status": state["status"]}

    return node


def _evented(db: Session, node_name: str, node: NodeFunction) -> NodeFunction:
    def wrapped(state: AnalysisState) -> dict[str, Any]:
        started = perf_counter()
        input_summary = _input_summary(node_name, state)
        _record_event(
            db,
            state=state,
            node_name=node_name,
            status="started",
            input_summary=input_summary,
            output_summary={},
            duration_ms=0,
            error_message=None,
            evidence=[],
        )
        try:
            output = node(state)
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            _record_event(
                db,
                state=state,
                node_name=node_name,
                status="failed",
                input_summary=input_summary,
                output_summary={},
                duration_ms=duration_ms,
                error_message=safe_error_message(exc),
                evidence=[],
            )
            db.commit()
            raise

        duration_ms = int((perf_counter() - started) * 1000)
        output_summary = _output_summary(node_name, output)
        _record_event(
            db,
            state=state,
            node_name=node_name,
            status="completed",
            input_summary=input_summary,
            output_summary=output_summary,
            duration_ms=duration_ms,
            error_message=None,
            evidence=_event_evidence(output),
        )
        db.commit()
        return output

    return wrapped


def _record_event(
    db: Session,
    *,
    state: AnalysisState,
    node_name: str,
    status: str,
    input_summary: dict[str, Any],
    output_summary: dict[str, Any],
    duration_ms: int,
    error_message: str | None,
    evidence: list[dict[str, Any]],
) -> None:
    db.add(
        DocumentWorkflowEvent(
            document_id=state["document_id"],
            analysis_request_id=state["analysis_request_id"],
            node_name=node_name,
            status=status,
            input_summary=input_summary,
            output_summary=output_summary,
            duration_ms=duration_ms,
            error_message=error_message,
            evidence=evidence,
        )
    )
    db.flush()


def _get_or_create_request(
    db: Session,
    *,
    document: Document,
    idempotency_key: str | None,
) -> DocumentAnalysisRequest:
    key = idempotency_key or f"document:{document.id}:analysis"
    request = db.scalar(
        select(DocumentAnalysisRequest).where(
            DocumentAnalysisRequest.document_id == document.id,
            DocumentAnalysisRequest.idempotency_key == key,
        )
    )
    if request is not None:
        return request
    request = DocumentAnalysisRequest(
        document_id=document.id,
        idempotency_key=key,
        status=DocumentProcessingStatus.UPLOADED.value,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def _is_terminal(status: str) -> bool:
    return status in {
        DocumentProcessingStatus.NEEDS_REVIEW.value,
        DocumentProcessingStatus.COMPLETED.value,
        DocumentProcessingStatus.PARTIALLY_COMPLETED.value,
    }


def _chunk_to_state(chunk: DocumentChunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.id,
        "page_number": chunk.page_number,
        "chunk_index": chunk.chunk_index,
        "section_heading": chunk.section_heading,
        "char_count": len(chunk.text),
    }


def _section_to_state(section: RetrievedSection) -> dict[str, Any]:
    return {
        "chunk_id": section.chunk_id,
        "page_number": section.page_number,
        "section_heading": section.section_heading,
        "text": section.text,
        "score": section.score,
        "matched_terms": section.matched_terms,
    }


def _state_to_section(raw: dict[str, Any]) -> RetrievedSection:
    return RetrievedSection(
        chunk_id=str(raw["chunk_id"]),
        page_number=int(raw["page_number"]),
        section_heading=raw.get("section_heading"),
        text=str(raw["text"]),
        score=int(raw["score"]),
        matched_terms=[str(term) for term in raw.get("matched_terms", [])],
    )


def _input_summary(node_name: str, state: AnalysisState) -> dict[str, Any]:
    return {
        "document_id": state["document_id"],
        "node": node_name,
        "page_chunk_count": len(state.get("page_chunks", [])),
        "relevant_section_count": len(state.get("relevant_sections", [])),
        "requirement_count": len(state.get("extracted_requirements", [])),
        "validation_error_count": len(state.get("validation_errors", [])),
    }


def _output_summary(node_name: str, output: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {"node": node_name}
    if "page_count" in output:
        summary["page_count"] = output["page_count"]
    if "page_chunks" in output:
        summary["page_chunk_count"] = len(output["page_chunks"])
    if "relevant_sections" in output:
        summary["relevant_section_count"] = len(output["relevant_sections"])
    if "extracted_requirements" in output:
        summary["requirement_count"] = len(output["extracted_requirements"])
    if "valid_requirements" in output:
        summary["valid_requirement_count"] = len(output["valid_requirements"])
    if "final_findings" in output:
        summary["final_finding_count"] = len(output["final_findings"])
    if "persisted_finding_count" in output:
        summary["persisted_finding_count"] = output["persisted_finding_count"]
    if "validation_errors" in output:
        summary["validation_error_count"] = len(output["validation_errors"])
    if "summary" in output:
        summary["summary"] = output["summary"]
    if "status" in output:
        summary["status"] = output["status"]
    return summary


def _event_evidence(output: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for item in output.get("valid_requirements", []):
        for raw_evidence in item.get("evidence", []):
            evidence.append(
                {
                    "page_number": raw_evidence.get("page_number"),
                    "section_name": raw_evidence.get("section_name"),
                    "excerpt": raw_evidence.get("excerpt"),
                }
            )
    return evidence
