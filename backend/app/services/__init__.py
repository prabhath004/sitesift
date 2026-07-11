"""Deterministic business logic.

Intentionally empty in the foundation. Everything in this package must be
reproducible without an LLM: CSV validation, unit normalization, threshold
checks, category and overall scoring, status assignment, ranking, report totals.

LLM-assisted work belongs in ``app.workflows``, never here.
"""
