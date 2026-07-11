"""ORM models.

Intentionally empty in the foundation. The backend-screening and
document-analysis agents own the tables described in the specification
(projects, candidate_sites, screening_runs, site_scores, risk_findings,
documents, evidence, reviews, workflow_events).

When adding a model:
1. Inherit from ``app.database.base.Base``.
2. Import it here so Alembic autogenerate discovers it.
3. Generate a migration: ``alembic revision --autogenerate -m "..."``.
"""
