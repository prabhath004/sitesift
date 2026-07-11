"""LLM-assisted workflows (LangGraph).

Intentionally empty in the foundation. The document-analysis agent owns the
permitting-document graph described in the specification.

Rules that apply to everything in this package:
- Never compute numbers here (acreage, distances, overlaps, scores). Call
  ``app.services`` for those.
- Every document-derived finding must carry evidence: document, page/section,
  and a verbatim excerpt.
- Failure here must leave deterministic screening results intact.
"""
