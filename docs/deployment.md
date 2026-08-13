# Production Deployment Guide — FireFlies Clone

This document details the production architecture, environment configuration, database management, container orchestration, and security considerations for deploying the FireFlies Clone application.

---

## 1. Deployment Architecture Overview

```
                        [ Browser Client ]
                                |
                         HTTP/HTTPS (Port 80/443)
                                |
                       [ Nginx Reverse Proxy ]
                     (Frontend SPA & API Router)
                                |
               +----------------+----------------+
               |                                 |
       Static Web Assets                  Proxy `/api/v1`
               |                                 |
      [ React Single Page App ]        [ FastAPI Backend Service ]
                                                |
                               +----------------+----------------+
                               |                                 |
                       [ PostgreSQL DB ]                [ Persistent Volume ]
                      (Port 5432 / Storage)              (/app/storage/audio)
                               ^                                 ^
                               |                                 |
                               +----------------+----------------+
                                                |
                                     [ Background Worker Runner ]
                                     (Persisted Job Processing)
```

---

## 2. Prerequisites

- **Docker Engine** (v20.10+) & **Docker Compose** (v2.0+)
- **Python** (v3.11+) (for local non-containerized testing)
- **Node.js** (v20+) & **npm** (v10+)
- **Google Gemini API Key** (for speech-to-text & AI intelligence generation)
- **Google OAuth 2.0 Credentials** (Client ID & Client Secret for Calendar Sync)

---

## 3. Environment Variable Configuration

### Backend Secrets (`backend/.env`)
These variables must **NEVER** be exposed to browser JavaScript:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Environment mode (`development` / `production`) | `production` |
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection URI | `postgresql://postgres:password@postgres:5432/fireflies` |
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens | `secure_32_character_random_string` |
| `AUDIO_STORAGE_PATH` | Absolute path to stored audio files | `/app/storage/audio` |
| `TRANSCRIPTION_PROVIDER` | STT provider (`gemini` or `mock`) | `gemini` |
| `GEMINI_API_KEY` | Google Gemini API Key | `AIzaSy...` |
| `GOOGLE_CLIENT_ID` | OAuth Client ID for Google Calendar | `xyz.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | OAuth Client Secret for Google Calendar | `GOCSPX-...` |
| `CORS_ORIGINS` | Comma-separated list of allowed origins | `http://localhost,http://yourdomain.com` |

### Frontend Variables (`frontend/.env`)
Only variables prefixed with `VITE_` are bundled into browser JS:

| Variable | Description | Value |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Base API route prefix | `/api/v1` |

---

## 4. Local Containerized Startup (Docker Compose)

1. Clone repository and navigate to root directory.
2. Create `backend/.env` based on `backend/.env.example`.
3. Launch the container stack:

```bash
docker-compose up --build -d
```

4. Verify all containers are healthy:

```bash
docker-compose ps
```

The stack starts:
- **`fireflies_postgres`**: PostgreSQL 15 database
- **`fireflies_backend`**: FastAPI application server (Port 8000)
- **`fireflies_worker`**: Standalone background worker process
- **`fireflies_frontend`**: Nginx web server serving React SPA (Port 80)

---

## 5. Database Migrations (Alembic)

Database schema updates are managed using Alembic migrations:

```bash
# Run migrations inside the backend container
docker-compose exec backend alembic upgrade head
```

To create a new migration after model changes:

```bash
docker-compose exec backend alembic revision --autogenerate -m "describe_changes"
```

---

## 6. Health & Readiness Probes

The backend exposes two production-grade health check routes:

- **Liveness Probe**: `GET /api/v1/health`
  - Returns `{"status": "ok", "app_name": "FireFlies Clone API", "version": "0.1.0"}`
- **Readiness Probe**: `GET /api/v1/health/ready`
  - Performs an active `SELECT 1` query against PostgreSQL.
  - Returns `200 OK` with `{"status": "ready", "database": "connected"}` when ready.
  - Returns `503 Service Unavailable` if database is unreachable (without leaking credentials or stack traces).

---

## 7. Persistent File Storage Architecture

- Meeting audio files are stored under `/app/storage/audio` via `LocalStorageService`.
- In `docker-compose.yml`, a persistent Docker volume `audio_data` is mounted to `/app/storage/audio` across both `backend` and `worker` containers.
- This ensures uploaded audio files survive container restarts and can be accessed by both API and background workers.
- **Future Scale**: `StorageService` abstract base class allows swapping `LocalStorageService` with an S3 / Google Cloud Storage adapter without modifying meeting business logic.

---

## 8. Security Considerations

1. **Secret Isolation**: Secrets (`GEMINI_API_KEY`, `JWT_SECRET_KEY`, `GOOGLE_CLIENT_SECRET`) are kept backend-only.
2. **CORS Restrictions**: In production (`ENVIRONMENT=production`), wildcard `*` origins are rejected by startup validation.
3. **Docs Restriction**: Interactive Swagger UI (`/docs`) and ReDoc (`/redoc`) are automatically disabled in production mode.
4. **Path Traversal Prevention**: `LocalStorageService` validates target file paths with `is_relative_to()` to prevent directory traversal attacks.
5. **IDOR & Multi-Tenant Isolation**: All workspace and meeting resources enforce server-side membership verification.
