# Address Book Service

A production-grade REST API for creating, managing, and geospatially querying address records. Built with **FastAPI**, **SQLAlchemy ORM**, **SQLite**, and **geopy**.

---

## Project Overview

The service exposes a versioned JSON API (`/api/v1`) that lets clients:

| Operation | Method | Path |
|---|---|---|
| Create address | `POST` | `/api/v1/addresses/` |
| Get address by ID | `GET` | `/api/v1/addresses/{id}` |
| Partially update address | `PATCH` | `/api/v1/addresses/{id}` |
| Delete address | `DELETE` | `/api/v1/addresses/{id}` |
| Find addresses within radius | `GET` | `/api/v1/addresses/nearby/search` |
| Health check | `GET` | `/health` |

Interactive API documentation is available at `http://127.0.0.1:8000/docs` after startup.

---

## Architecture

```
app/
├── main.py                     # FastAPI application factory, lifespan, global error handler
├── core/
│   ├── config.py               # Pydantic-settings — reads from environment / .env
│   └── logging.py              # Structured logging configuration
├── db/
│   ├── base.py                 # SQLAlchemy DeclarativeBase
│   └── session.py              # Engine, SessionLocal, get_db dependency
├── models/
│   └── address.py              # SQLAlchemy ORM model
├── schemas/
│   └── address.py              # Pydantic request/response schemas with validation
├── repositories/
│   └── address_repository.py   # Data-access layer (all ORM operations)
├── services/
│   └── address_service.py      # Business logic, error handling, logging
├── api/
│   └── routes/
│       └── address_routes.py   # FastAPI router — HTTP layer only
└── utils/
    └── geo.py                  # Geospatial helper using geopy geodesic distance

tests/
├── conftest.py                 # Pytest fixtures, in-memory test DB, TestClient
└── test_address_crud.py        # Full CRUD + geospatial test suite
```

**Layer responsibilities:**

- **Routes** — parse HTTP, delegate to service, return responses.
- **Service** — orchestrate business rules, raise `HTTPException` on failures.
- **Repository** — single responsibility: ORM read/write; zero business logic.
- **Utils** — pure, stateless helpers (geospatial calculations).

---

## Running the Application

### 1. Clone and set up environment

```bash
git clone <repo-url>
cd eastvantage_addressbook_service

python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows
venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env if you need a different DATABASE_URL or LOG_LEVEL
```

### 4. Start the server

```bash
uvicorn app.main:app --reload
```

The API is now available at `http://127.0.0.1:8000`.

---

## Running with Docker

```bash
docker build -t addressbook-service .
docker run -p 8000:8000 --env-file .env addressbook-service
```

---

## Example curl Requests

### Create an address

```bash
curl -X POST http://127.0.0.1:8000/api/v1/addresses/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Eiffel Tower",
    "street": "Champ de Mars, 5 Av. Anatole France",
    "city": "Paris",
    "country": "France",
    "latitude": 48.8584,
    "longitude": 2.2945
  }'
```

### Get an address by ID

```bash
curl http://127.0.0.1:8000/api/v1/addresses/1
```

### Update an address (partial)

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/addresses/1 \
  -H "Content-Type: application/json" \
  -d '{"city": "Paris (updated)"}'
```

### Delete an address

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/addresses/1
```

### Find addresses within 10 km of a coordinate

```bash
curl "http://127.0.0.1:8000/api/v1/addresses/nearby/search?latitude=48.8584&longitude=2.2945&radius_km=10"
```

---

## Running Tests

```bash
pytest tests/ -v
```

Test coverage includes:
- Full CRUD happy paths and edge cases
- Input validation (invalid lat/lon, missing fields)
- 404 handling for non-existent resources
- Geospatial radius filtering (nearby vs. distant addresses)

Each test uses an isolated SQLite database with transaction rollback between tests — no test pollution.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./addressbook.db` | SQLAlchemy connection string |
| `LOG_LEVEL` | `INFO` | Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## HTTP Status Codes

| Code | Meaning |
|---|---|
| `201 Created` | Address successfully created |
| `200 OK` | Successful retrieval or update |
| `204 No Content` | Address successfully deleted |
| `400 Bad Request` | Malformed request body |
| `404 Not Found` | Address ID does not exist |
| `422 Unprocessable Entity` | Validation error (e.g., invalid coordinates) |
| `500 Internal Server Error` | Unexpected server-side failure |
