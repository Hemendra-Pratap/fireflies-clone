# Backend

Lean FastAPI backend scaffold with:

- application entrypoint
- configuration and database session wiring
- versioned API router layout
- SQLAlchemy model base and shared mixins
- Alembic migration configuration for SQLite

## Start

```powershell
pip install -r .\backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

## Migrations

```powershell
alembic -c .\backend\alembic.ini upgrade head
```
