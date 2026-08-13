# FireFlies Clone

Minimal monorepo scaffold with:

- `frontend/` reserved for the future UI
- `backend/` containing a startable FastAPI application skeleton

## Backend

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

The API will be available at `http://127.0.0.1:8000`, with docs at `/docs`.

## Database Migrations

Alembic is configured under `backend/alembic/`.

From the repository root:

```powershell
alembic -c .\backend\alembic.ini upgrade head
```
