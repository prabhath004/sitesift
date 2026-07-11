# Migrations

Alembic is wired up but there are **no migrations yet** — the foundation ships
no ORM models, so there is no schema to migrate.

The first feature agent to add a model creates the initial revision:

```bash
cd backend
alembic revision --autogenerate -m "create projects and candidate_sites"
alembic upgrade head
```

`alembic/env.py` takes `DATABASE_URL` from `app.core.config.Settings`, so
migrations always target the same database as the running app.

`alembic/versions/` is a high-conflict directory across parallel worktrees: two
agents generating a revision independently will both branch from the same
`down_revision`. Coordinate, or expect the integration agent to linearize the
history with `alembic merge`.
