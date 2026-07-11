"""User-safe exceptions for the document-analysis vertical slice."""

from __future__ import annotations


class DocumentError(Exception):
    """Base class for expected document-analysis failures."""

    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DocumentError):
    status_code = 404


class ConflictError(DocumentError):
    status_code = 409


class TransientAnalysisError(DocumentError):
    status_code = 503


class InvalidModelOutputError(DocumentError):
    status_code = 422


def safe_error_message(error: Exception) -> str:
    """Return a client-safe error message without stack traces or secrets."""
    if isinstance(error, DocumentError):
        return error.message
    return "Document analysis failed. Review workflow events for the failed step."
