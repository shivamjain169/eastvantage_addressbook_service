# Address Book Service — Technical Documentation

**Version:** 1.0.0
**Stack:** Python 3.10+ · FastAPI · SQLAlchemy 2.x ORM · SQLite · Pydantic v2 · geopy
**Author:** Senior Backend Engineer

---

## Table of Contents

1. [Service Overview](#1-service-overview)
2. [Architectural Philosophy](#2-architectural-philosophy)
3. [Project Structure Deep Dive](#3-project-structure-deep-dive)
4. [Layer-by-Layer Technical Breakdown](#4-layer-by-layer-technical-breakdown)
   - 4.1 [Configuration — `core/config.py`](#41-configuration--coreconfigpy)
   - 4.2 [Logging — `core/logging.py`](#42-logging--coreloggingpy)
   - 4.3 [Database Base — `db/base.py`](#43-database-base--dbbasepy)
   - 4.4 [Database Session — `db/session.py`](#44-database-session--dbsessionpy)
   - 4.5 [ORM Model — `models/address.py`](#45-orm-model--modelsaddresspy)
   - 4.6 [Schemas — `schemas/address.py`](#46-schemas--schemasaddresspy)
   - 4.7 [Repository — `repositories/address_repository.py`](#47-repository--repositoriesaddress_repositorypy)
   - 4.8 [Service — `services/address_service.py`](#48-service--servicesaddress_servicepy)
   - 4.9 [Routes — `api/routes/address_routes.py`](#49-routes--apiroutesaddress_routespy)
   - 4.10 [Geo Utility — `utils/geo.py`](#410-geo-utility--utilsgeopy)
   - 4.11 [Application Entry Point — `main.py`](#411-application-entry-point--mainpy)
5. [Request Lifecycle — End to End](#5-request-lifecycle--end-to-end)
6. [Data Flow Diagrams](#6-data-flow-diagrams)
7. [Validation Strategy](#7-validation-strategy)
8. [Error Handling Strategy](#8-error-handling-strategy)
9. [Logging Strategy](#9-logging-strategy)
10. [Dependency Injection Design](#10-dependency-injection-design)
11. [Geospatial Distance Calculation](#11-geospatial-distance-calculation)
12. [Testing Architecture](#12-testing-architecture)
13. [Design Decisions & Trade-offs](#13-design-decisions--trade-offs)
14. [SOLID Principles Applied](#14-solid-principles-applied)
15. [Security Considerations](#15-security-considerations)
16. [Future Scope & Roadmap](#16-future-scope--roadmap)

---

## 1. Service Overview

The Address Book Service is a RESTful HTTP API that allows consumers to manage a registry of physical addresses and perform geospatial proximity queries against them.

### Capabilities

| Capability | HTTP Method | Endpoint |
|---|---|---|
| Create an address | `POST` | `/api/v1/addresses/` |
| Retrieve an address by ID | `GET` | `/api/v1/addresses/{id}` |
| Partially update an address | `PATCH` | `/api/v1/addresses/{id}` |
| Delete an address | `DELETE` | `/api/v1/addresses/{id}` |
| Find addresses within a radius | `GET` | `/api/v1/addresses/nearby/search` |
| Health check | `GET` | `/health` |

### Core Design Goals

- **Correctness** — every input is validated before it reaches the database; invalid data is rejected at the boundary.
- **Clarity** — each layer has a single, obvious responsibility. A new engineer can navigate the codebase without guidance.
- **Safety** — internal errors never leak stack traces or database details to API consumers.
- **Testability** — every layer is independently testable. The database layer can be swapped in tests without changing any business logic.
- **Maintainability** — adding a new endpoint, field, or rule requires changes in exactly the expected place, nowhere else.

---

## 2. Architectural Philosophy

The service follows a **Layered Architecture** (also called N-Tier or Clean Architecture lite). The core principle is the **dependency rule**: outer layers depend on inner layers, never the reverse.

```
┌──────────────────────────────────────┐
│            HTTP / Routes             │  ← Knows: HTTP verbs, status codes, request/response shapes
├──────────────────────────────────────┤
│              Service                 │  ← Knows: business rules, orchestration, error policy
├──────────────────────────────────────┤
│            Repository                │  ← Knows: SQLAlchemy ORM, database operations only
├──────────────────────────────────────┤
│         Model / Schema / Utils       │  ← Knows: data shape, validation rules, pure functions
└──────────────────────────────────────┘
```

**Why layered architecture for a service this size?**

Even for a small service, flat architecture (putting everything in one file or one layer) creates problems the moment requirements change:

- If validation logic lives in route handlers, you cannot test it without spinning up HTTP.
- If business logic lives in repositories, you cannot swap the database without rewriting business rules.
- If logging is scattered everywhere, you get inconsistent log formats and duplicated code.

Layering enforces natural seams — each seam is a testability boundary, a replaceability boundary, and a reasoning boundary.

---

## 3. Project Structure Deep Dive

```
app/
├── main.py                         # Application factory and wiring
├── core/
│   ├── config.py                   # Environment-driven settings
│   └── logging.py                  # Centralised logging setup
├── db/
│   ├── base.py                     # ORM declarative base
│   └── session.py                  # Engine, session factory, get_db dependency
├── models/
│   └── address.py                  # SQLAlchemy ORM table definition
├── schemas/
│   └── address.py                  # Pydantic I/O contracts
├── repositories/
│   └── address_repository.py       # Database access — read/write only
├── services/
│   └── address_service.py          # Business logic and error policy
├── api/
│   └── routes/
│       └── address_routes.py       # HTTP endpoints and DI wiring
└── utils/
    └── geo.py                      # Pure geospatial helper function

tests/
├── conftest.py                     # Test fixtures and DB override
└── test_address_crud.py            # Comprehensive test suite
```

The directory names themselves communicate intent. `core/` holds cross-cutting infrastructure. `db/` holds database wiring. `models/` holds persistence definitions. `schemas/` holds API contracts. The separation between `models/` and `schemas/` is one of the most important separations in the entire codebase — explained in detail in section 4.

---

## 4. Layer-by-Layer Technical Breakdown

### 4.1 Configuration — `core/config.py`

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    DATABASE_URL: str = "sqlite:///./addressbook.db"
    LOG_LEVEL: str = "INFO"

settings = Settings()
```

**What it does:** Reads all configuration from environment variables (or a `.env` file during development) using `pydantic-settings`. Exposes a module-level `settings` singleton that the rest of the application imports.

**Why `pydantic-settings` instead of `os.environ.get()`?**

- `os.environ.get("KEY", "default")` scattered across the codebase means configuration is undiscoverable — you have to grep the entire project to find every variable the app reads.
- `pydantic-settings` gives you one class that is the complete, documented contract of what the application needs to run. Missing a required variable fails fast at startup, not at runtime when that code path is hit.
- It provides automatic type coercion: a `LOG_LEVEL: str` field reads from `LOG_LEVEL=DEBUG` in the environment without any manual parsing.
- Defaults are co-located with the field definition, making the "safe fallback" value obvious.

**Why a module-level singleton?**

The `settings` object is imported directly (`from app.core.config import settings`). This is intentional — settings do not change at runtime, so they do not need to be injected as a dependency. Injecting them would add ceremony with no benefit.

---

### 4.2 Logging — `core/logging.py`

```python
def configure_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    ...

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
```

**What it does:** Configures a single root handler on startup. Every module calls `get_logger(__name__)` to receive a named logger that participates in the hierarchy.

**Why `%(name)s` in the format?**

When a log line appears in production, you need to know which module produced it without reading a stack trace. `%(name)s` prints the full dotted module path, e.g. `app.services.address_service`. You can immediately identify:

- Which layer produced the log (service, repository, route)
- Which domain it belongs to (address)

**Why `sys.stdout` instead of `sys.stderr`?**

Container orchestrators (Docker, Kubernetes) collect stdout and stderr as separate streams. Application logs belong on stdout. Only truly exceptional OS-level errors belong on stderr. This ensures logs flow correctly into log aggregators like CloudWatch, Datadog, or Loki without configuration.

**Why silence `sqlalchemy.engine` and `uvicorn.access`?**

Both of these are extremely verbose at DEBUG level and produce noise that obscures application-level logs. They are set to WARNING — they will still surface genuine problems but will not flood the log stream with routine query execution or HTTP access entries. Application-level request logging is handled explicitly in the route handlers instead, where the format and content is under our control.

**Why `configure_logging()` is called in `main.py` before anything else?**

Python's logging system is global. If any module instantiates a logger before `configure_logging()` is called, it receives the default (no-op) configuration and its first log messages may be lost. Calling it as the very first line of `main.py` ensures the handler is in place before any import side effects or logger instantiations occur.

---

### 4.3 Database Base — `db/base.py`

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

**What it does:** Defines the single `Base` class that all ORM models inherit from.

**Why a separate file for just this?**

`Base` is imported by both model files (to define tables) and `main.py` (to call `Base.metadata.create_all()`). If `Base` lived inside a model file (e.g., `models/address.py`), then `main.py` would need to import from a model file purely for infrastructure reasons — a leaky coupling. Keeping `Base` in `db/base.py` makes the import graph clean:

```
models/address.py  →  db/base.py
main.py            →  db/base.py  (not models/address.py)
```

It also avoids circular import issues as the model count grows.

---

### 4.4 Database Session — `db/session.py`

```python
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Why `autocommit=False`?**

With `autocommit=False`, every operation on a session is part of an implicit transaction. The transaction is only committed when `.commit()` is called explicitly (which happens in the repository). This means:

- Multiple operations can be grouped atomically.
- An exception mid-operation does not partially commit data.
- You have a clear, explicit moment when data becomes durable.

With `autocommit=True`, every statement commits immediately. This makes it impossible to roll back a partially completed multi-step operation.

**Why `autoflush=False`?**

`autoflush=True` causes SQLAlchemy to flush pending changes to the database before each query, even if you have not committed yet. This can cause unexpected `IntegrityError` exceptions at read time (not write time), making bugs confusing to diagnose. `autoflush=False` means flushes happen at `.commit()` time, which is predictable and explicit.

**Why `check_same_thread=False`?**

SQLite's default threading model prohibits sharing a connection across threads. FastAPI uses a thread pool for synchronous route handlers, so requests run in worker threads. Without this flag, the application would crash on the second request. This flag is SQLite-specific and is safe in this context because SQLAlchemy manages its own session isolation.

**Why `echo=False`?**

`echo=True` prints every SQL statement to stdout, which is extremely useful during active development but catastrophic in production — it doubles log volume, leaks table/column names, and can expose sensitive data in query parameters. It should be enabled temporarily via an environment variable or debug flag, not hardcoded.

**Why a generator function with `try/finally`?**

The `get_db()` function is a FastAPI dependency. The `yield` makes it a generator dependency. FastAPI guarantees the code after `yield` (the `finally` block) runs after the request handler completes — whether or not an exception occurred. This ensures the session is always closed and the connection is returned to the pool, preventing connection leaks.

---

### 4.5 ORM Model — `models/address.py`

```python
class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ...
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Why `Mapped[T]` and `mapped_column()` (SQLAlchemy 2.x style)?**

SQLAlchemy 2.0 introduced the `Mapped` annotation style. It provides full Python type hints on model attributes, which means:

- IDEs can infer the type of `address.name` as `str`, not `InstrumentedAttribute`.
- Static analysis tools (mypy, pyright) can catch type errors in code that uses the model.
- The intent (`Mapped[str]` means non-nullable, `Mapped[str | None]` means nullable) is expressed in Python rather than buried in column kwargs.

**Why `index=True` on `id`?**

The primary key column is the most commonly queried column (every `get_by_id` call uses it). SQLite creates a primary key index automatically, but being explicit documents the intent and ensures correctness when migrating to other databases.

**Why `server_default=func.now()` instead of `default=datetime.utcnow`?**

`default=datetime.utcnow` sets the value in Python before the INSERT. This has two problems:
1. The timestamp is generated by the application server clock, not the database clock. In distributed or replicated setups, these can diverge.
2. `datetime.utcnow` is not timezone-aware and is deprecated in Python 3.12+.

`server_default=func.now()` delegates timestamp generation to the database engine itself, ensuring consistency, timezone awareness, and correct behaviour even if records are inserted via tools other than the application.

**Why `onupdate=func.now()` on `updated_at`?**

SQLAlchemy's `onupdate` hook fires automatically when `.commit()` is called on a dirty (modified) session object. This means `updated_at` is always accurate without any manual code in the repository or service — the ORM handles it transparently.

**Why `nullable=False` on every field?**

Explicit nullability constraints are enforced at the database level, not just the application level. If a bug in the application ever bypasses Pydantic validation (e.g., a direct database script or a future code path), the database itself will reject incomplete records. Defense in depth.

---

### 4.6 Schemas — `schemas/address.py`

```python
class AddressBase(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

    @field_validator("name", "street", "city", "country", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        ...

class AddressCreate(AddressBase): pass

class AddressUpdate(BaseModel):
    name: str | None = Field(default=None, ...)

class AddressResponse(AddressBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
```

**Why are `models/` and `schemas/` separate?**

This separation is fundamental and often misunderstood. They serve completely different purposes:

| Concern | ORM Model (`models/`) | Pydantic Schema (`schemas/`) |
|---|---|---|
| Purpose | Database table definition | API contract (input/output shape) |
| Validation | Database constraints (nullable, length) | Business rules (coordinate bounds, required fields) |
| Coupling | Tied to SQLAlchemy | Tied to HTTP/JSON |
| Lifecycle | Persists in the database | Lives for one request/response cycle |

If you use the ORM model directly as the API response, you expose your database schema to API consumers. Any refactor of your table structure is immediately a breaking API change. With separate schemas, you can refactor the database without changing the API and vice versa.

**Why `AddressCreate` inherits `AddressBase` but `AddressUpdate` does not?**

`AddressCreate` requires all fields — no field is optional when creating a new record. It inherits `AddressBase` directly, reusing all field definitions and validators.

`AddressUpdate` (partial update / PATCH semantics) allows any subset of fields. Every field is `Optional` with `default=None`. It cannot inherit `AddressBase` because `AddressBase` marks all fields as required (`...`). The two schemas have genuinely different field optionality contracts, so they must be separate.

**Why `model_dump(exclude_unset=True)` in the repository's update method?**

When a client sends `{"city": "Lyon"}`, Pydantic creates an `AddressUpdate` where `name`, `street`, `country`, `latitude`, `longitude` are all `None` (the default). Without `exclude_unset=True`, the repository would set all of those fields to `None` in the database — corrupting existing data. `exclude_unset=True` includes only fields that were explicitly provided in the request body, preserving all others.

**Why `field_validator` with `mode="before"`?**

`mode="before"` runs the validator before Pydantic's own type coercion. This is the correct mode for normalisation (stripping whitespace) because you want to normalise the raw input before it is parsed and stored. If it ran `mode="after"`, Pydantic would have already accepted `"  Paris  "` as a valid `str` and the validator would run on the already-accepted value — which also works, but `mode="before"` is semantically cleaner for pre-processing.

**Why `ConfigDict(from_attributes=True)` on `AddressResponse`?**

FastAPI's response serialisation calls `AddressResponse.model_validate(address_orm_object)`. Without `from_attributes=True`, Pydantic expects a dictionary. With it, Pydantic reads attributes directly from the SQLAlchemy ORM object. This is the bridge that allows returning ORM model instances from service methods and having them automatically serialised into the correct response shape.

---

### 4.7 Repository — `repositories/address_repository.py`

```python
class AddressRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, payload: AddressCreate) -> Address:
        address = Address(**payload.model_dump())
        self._db.add(address)
        self._db.commit()
        self._db.refresh(address)
        return address

    def get_by_id(self, address_id: int) -> Address | None:
        return self._db.get(Address, address_id)

    def update(self, address: Address, payload: AddressUpdate) -> Address:
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(address, field, value)
        self._db.commit()
        self._db.refresh(address)
        return address
```

**What this layer is responsible for:** One thing only — translating between Python objects and the database. No business logic. No error handling. No HTTP concepts.

**Why `self._db.get(Address, address_id)` instead of a query?**

`Session.get()` first checks the SQLAlchemy identity map (an in-memory cache of objects loaded in the current session). If the object is already loaded, it returns the cached instance without hitting the database. This is more efficient than `.query(Address).filter(Address.id == address_id).first()` which always generates a SELECT. For PK lookups — which are the most common lookup — `get()` is the correct API.

**Why `db.refresh(address)` after commit?**

After `db.commit()`, SQLAlchemy expires all attributes on session-tracked objects. This is because the database may have modified values during the commit (e.g., `server_default`, `onupdate` triggers). Without `refresh()`, the next access to any attribute would trigger a lazy load. Calling `refresh()` immediately populates all attributes in a single SELECT, returning a fully-populated object to the service layer.

**Why does the repository have no try/except?**

The repository is a pure data-access layer. It does not know what the caller intends to do if the database fails. It does not know about HTTP status codes. It does not know about log severity policies. Any exception it raises will naturally propagate up to the service layer, where all of these decisions are made. Adding try/except here would either:
- Swallow exceptions silently (dangerous)
- Re-raise them immediately (pointless boilerplate)
- Partially handle them (wrong layer for that responsibility)

---

### 4.8 Service — `services/address_service.py`

```python
class AddressService:
    def __init__(self, repository: AddressRepository) -> None:
        self._repo = repository

    def create_address(self, payload: AddressCreate) -> Address:
        logger.info("Creating address: name=%r city=%r", payload.name, payload.city)
        try:
            address = self._repo.create(payload)
            logger.info("Address created successfully: id=%d", address.id)
            return address
        except Exception as exc:
            logger.error("Failed to create address: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail="...") from exc
```

**What this layer is responsible for:**

- Orchestrating the sequence of operations needed to fulfil a use case.
- Enforcing business rules (e.g., "an address must exist before it can be updated").
- Deciding what constitutes an error and what HTTP status code it maps to.
- Logging meaningful events at the right severity level.

**Why does the service accept and return domain objects (not schemas)?**

The service operates on `Address` ORM objects rather than dicts or Pydantic models. This keeps the service's interface stable — it does not need to change if the JSON representation of an address changes. The route layer handles the translation from schema to domain object (via Pydantic) and from domain object back to schema (via `response_model`).

**Why `raise HTTPException(...) from exc`?**

The `from exc` clause is Python's exception chaining syntax. It preserves the original exception as `__cause__` on the new exception. This means:
1. In the logs (`exc_info=True`), the full original traceback is visible to developers.
2. The `HTTPException` with a safe, user-facing message is what propagates to the route handler and is serialised into the response.
3. Internal details (SQL errors, column names) never reach the API consumer.

**Why check for `None` before calling `repo.update()` / `repo.delete()`?**

The repository's `update()` and `delete()` methods accept an already-fetched `Address` object — they do not take an ID and look it up themselves. This is intentional: the service must verify the record exists and is accessible before handing it to the repository. This gives the service full control over the 404 logic, including the log message, rather than having the repository make that determination implicitly.

---

### 4.9 Routes — `api/routes/address_routes.py`

```python
router = APIRouter(prefix="/addresses", tags=["Addresses"])

def get_address_service(db: Session = Depends(get_db)) -> AddressService:
    return AddressService(AddressRepository(db))

@router.post("/", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_address(payload: AddressCreate, service: AddressService = Depends(get_address_service)):
    return service.create_address(payload)
```

**What this layer is responsible for:** HTTP only. Parse the request, call the service, return the response. Nothing else.

**Why `APIRouter` instead of putting routes on `app` directly?**

`APIRouter` allows routes to be defined in their own module and mounted on the app with a prefix. This means:
- Route files are self-contained and independently readable.
- Adding a new resource (e.g., `contacts`) requires only creating a new router file and one line in `main.py`.
- The `prefix="/api/v1"` is applied at mount time in `main.py`, keeping versioning concerns out of the route file itself.

**Why `status.HTTP_201_CREATED` explicitly on POST?**

FastAPI defaults to `200 OK` for all routes. A `POST` that creates a new resource should return `201 Created` per RFC 7231. This is a semantic distinction that matters — automated API clients, API gateways, and contract tests rely on correct status codes. Using the `status` enum (not a raw integer) makes the intent readable and prevents typos.

**Why `status.HTTP_204_NO_CONTENT` for DELETE with `-> None` return type?**

`204` means "the request succeeded but there is no body to return." Returning `None` from the handler, combined with `status_code=204`, tells FastAPI to generate a response with an empty body. Returning `{"message": "deleted"}` with a 204 would be incorrect — 204 must have no body per the HTTP specification.

**Why use `Query(...)` validators on the nearby search endpoint?**

The nearby search parameters arrive as query string parameters, not a JSON body. FastAPI's `Query()` applies the same `ge`/`le`/`gt` constraints at the HTTP layer, before the request reaches the service. This means invalid coordinates are rejected with `422` without touching the service or database — consistent with how body validation works via Pydantic schemas.

**Why `PATCH` instead of `PUT` for updates?**

`PUT` replaces the entire resource — the client must send all fields, even unchanged ones. `PATCH` applies a partial update — the client sends only the fields it wants to change. Since `AddressUpdate` uses optional fields and `exclude_unset=True`, PATCH semantics are fully supported and far more practical for API consumers.

---

### 4.10 Geo Utility — `utils/geo.py`

```python
from geopy.distance import geodesic

def is_within_radius(center_lat, center_lon, address, radius_km) -> bool:
    center = (center_lat, center_lon)
    point = (address.latitude, address.longitude)
    distance_km = geodesic(center, point).kilometers
    return distance_km <= radius_km
```

**Why `geopy.distance.geodesic` and not a manual Haversine formula?**

The Haversine formula is widely copied from Stack Overflow, but it assumes the Earth is a perfect sphere. The actual shape of the Earth is an oblate spheroid — it is wider at the equator than at the poles by about 21 km. For addresses near the poles, Haversine can accumulate errors of up to 0.5%.

`geodesic` uses Vincenty's formulae (or Karney's method in recent geopy versions), which model the Earth's actual ellipsoidal shape. It is battle-tested, actively maintained, handles edge cases (antipodal points, polar regions), and is accurate to within millimetres. There is no reason to re-implement this.

**Why is this a `utils/` function rather than a method on the model?**

The calculation is a pure function — it depends only on its inputs and has no side effects. It does not need to know about sessions, requests, or any other service state. Keeping it in `utils/` signals that it is a stateless helper that can be imported and tested in complete isolation from the rest of the application.

---

### 4.11 Application Entry Point — `main.py`

```python
configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Address Book Service shutting down")

app = FastAPI(title="...", lifespan=lifespan)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc) -> JSONResponse:
    logger.error("Unhandled exception...", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "..."})

app.include_router(address_router, prefix="/api/v1")
```

**Why `lifespan` instead of `@app.on_event("startup")`?**

`on_event("startup")` is deprecated in FastAPI. The `lifespan` context manager is the modern replacement. It has a key advantage: the code before `yield` is startup logic, and the code after `yield` is shutdown logic — both are in one function, making the resource lifecycle easy to read and reason about. It also integrates properly with the ASGI lifespan protocol.

**Why `Base.metadata.create_all()` in lifespan instead of a migration tool?**

`create_all()` is appropriate for this stage because it is idempotent (safe to call on every startup) and keeps the service self-contained. In production with a real PostgreSQL database, this would be replaced by Alembic migrations, which provide versioned, reversible schema changes. See section 16.

**Why a global `exception_handler(Exception)` in `main.py`?**

This is the last line of defence. If any exception escapes all service-level try/except blocks — an unexpected bug, a third-party library raising an undocumented exception — this handler catches it, logs it with full traceback, and returns a safe `500` response. Without this, FastAPI would return its own default error response which may expose stack trace details depending on the `debug` setting. It ensures the contract "API consumers never see internal implementation details" holds unconditionally.

**Why `prefix="/api/v1"` at mount time?**

API versioning via URL prefix is applied when mounting the router, not inside the route file. This means:
- The route file itself is version-agnostic.
- Adding a `v2` router in the future requires zero changes to the existing route file.
- The version is a deployment/wiring concern, not a business logic concern.

---

## 5. Request Lifecycle — End to End

A `POST /api/v1/addresses/` request travels through the following steps:

```
1. HTTP request arrives at uvicorn ASGI server

2. FastAPI parses the URL and matches the route:
   POST /api/v1/addresses/  →  create_address()

3. FastAPI runs dependency resolution:
   get_db()              → opens a Session from the connection pool
   get_address_service() → instantiates AddressRepository(db), AddressService(repo)

4. FastAPI deserialises the JSON body into AddressCreate via Pydantic:
   - Strips whitespace from string fields (field_validator, mode="before")
   - Validates latitude is in [-90, 90]
   - Validates longitude is in [-180, 180]
   - Validates min/max lengths on string fields
   → If validation fails: returns 422 immediately (service never called)

5. Route handler calls service.create_address(payload)

6. Service logs the intent: "Creating address: name=... city=..."

7. Service calls repository.create(payload)

8. Repository:
   - Calls payload.model_dump() → {'name': ..., 'latitude': ..., ...}
   - Instantiates Address(**data)
   - Calls db.add(address)
   - Calls db.commit()  → issues INSERT to SQLite
   - Calls db.refresh(address)  → SELECT to populate server-generated fields
   - Returns Address ORM instance

9. Service logs success: "Address created successfully: id=1"
   Returns Address instance to route handler

10. FastAPI serialises Address ORM instance into AddressResponse via Pydantic:
    - from_attributes=True reads ORM object attributes
    - Produces JSON with id, name, street, city, country, latitude, longitude, created_at, updated_at

11. FastAPI sends HTTP 201 with JSON body

12. get_db() finally block runs: db.close() → connection returned to pool
```

---

## 6. Data Flow Diagrams

### Create Address

```
Client
  │  POST /api/v1/addresses/  {name, street, city, country, lat, lon}
  ▼
FastAPI (Pydantic validation)
  │  AddressCreate validated ✓ or 422 ✗
  ▼
AddressService.create_address(payload)
  │  try/except wraps the call
  ▼
AddressRepository.create(payload)
  │  model_dump() → Address(**data)
  │  db.add() → db.commit() → db.refresh()
  ▼
SQLite (INSERT INTO addresses ...)
  │  returns auto-generated id, created_at, updated_at
  ▼
AddressRepository → returns Address ORM object
  ▼
AddressService → returns Address ORM object + logs
  ▼
FastAPI (AddressResponse serialisation)
  │  from_attributes reads ORM attributes
  ▼
Client  ←  HTTP 201  {id, name, street, city, country, lat, lon, created_at, updated_at}
```

### Nearby Address Search

```
Client
  │  GET /api/v1/addresses/nearby/search?latitude=X&longitude=Y&radius_km=Z
  ▼
FastAPI (Query() validation on lat/lon/radius)
  │  NearbyQuery constructed ✓ or 422 ✗
  ▼
AddressService.get_nearby_addresses(query)
  ▼
AddressRepository.get_all()
  │  SELECT * FROM addresses
  ▼
[Address list]
  ▼
Python list comprehension with is_within_radius() filter
  │  For each address:
  │    geopy.geodesic((query_lat, query_lon), (addr.lat, addr.lon)).km
  │    include if distance <= radius_km
  ▼
Filtered [Address list]
  ▼
FastAPI  →  list[AddressResponse] serialised
  ▼
Client  ←  HTTP 200  [{...}, {...}]
```

---

## 7. Validation Strategy

Validation is applied at multiple levels (defense in depth):

| Level | Tool | What it catches |
|---|---|---|
| HTTP / Query params | FastAPI `Query(ge=, le=, gt=)` | Invalid coordinates in GET query strings |
| Request body | Pydantic `Field(ge=, le=, min_length=)` | Invalid JSON body values |
| Pre-processing | `field_validator(mode="before")` | Whitespace-padded strings |
| Database | `nullable=False`, `String(N)` | Missing required fields, oversized values |

**Why validate at multiple levels rather than just Pydantic?**

No single layer is immune to bypass. Direct database access (scripts, migrations, other services) bypasses Pydantic entirely. If the database has no constraints, corrupted data can enter. If Pydantic has no constraints, the database is the only guard. Multiple layers ensure correctness even if one layer is bypassed.

---

## 8. Error Handling Strategy

The error handling architecture follows a single principle: **each layer handles errors at the correct level of abstraction.**

```
Database error (e.g., SQLAlchemyError)
    │
    │  ← repository does NOT catch this
    │
    ▼
Service layer try/except catches Exception
    │  logs full traceback with exc_info=True (visible to developers)
    │  raises HTTPException with safe message (visible to API consumers)
    │
    ▼
FastAPI serialises HTTPException → {"detail": "safe message"} + HTTP 5xx
    │
    │  ← if HTTPException is raised (not caught by service), falls through to:
    ▼
Global exception_handler in main.py (last resort for truly unexpected exceptions)
    │  logs + returns generic 500
    ▼
Client receives: {"detail": "An unexpected internal server error occurred."}
```

**Key properties:**

- Stack traces are visible in server logs (for developers) but never in API responses (for consumers).
- The 404 vs 500 distinction is made at the service layer, where the business reason is known.
- The global handler is a safety net, not a primary error path.

---

## 9. Logging Strategy

Every significant event is logged with context:

| Event | Level | Example |
|---|---|---|
| Operation intent | `INFO` | `Creating address: name='Eiffel Tower' city='Paris'` |
| Operation success | `INFO` | `Address created successfully: id=1` |
| Resource not found | `WARNING` | `Address not found: id=999` |
| Database / unexpected failure | `ERROR` | `Failed to create address: ...` (with `exc_info=True`) |
| Startup / shutdown | `INFO` | `Starting Address Book Service` |

**Why `%r` for string values in log messages?**

`%r` uses `repr()` on the value, which wraps strings in quotes and escapes special characters. `logger.info("name=%r", "O'Brien's Place")` produces `name="O'Brien's Place"` rather than `name=O'Brien's Place`. This makes log values unambiguous and safe even when they contain spaces, newlines, or quotes.

**Why log both intent and success (two log lines per operation)?**

A single "success" log at the end does not tell you anything if the operation hangs or is still in progress when you look at the logs. The intent log (`Creating address: ...`) establishes a timeline entry when the work starts. If you see an intent log without a success log, the operation failed or is stuck. This is especially important in high-throughput systems where requests interleave.

---

## 10. Dependency Injection Design

FastAPI's DI system is used to wire the database session → repository → service chain cleanly:

```python
def get_db() -> Generator[Session, None, None]:       # db/session.py
    ...

def get_address_service(db: Session = Depends(get_db)) -> AddressService:
    return AddressService(AddressRepository(db))      # routes/address_routes.py

@router.post("/")
def create_address(service: AddressService = Depends(get_address_service)):
    ...
```

**Why this matters:**

The route handler does not instantiate the service directly. It declares what it needs (`AddressService`) and FastAPI resolves the entire chain automatically per request. This achieves:

- **Testability** — in tests, `get_db` is overridden with a fixture session: `app.dependency_overrides[get_db] = override_get_db`. This substitutes the test database without changing a single line of business logic.
- **One session per request** — every request gets its own `Session` instance, ensuring transaction isolation. Sessions are not shared across concurrent requests.
- **Automatic cleanup** — FastAPI calls the `finally` block of `get_db()` after the request completes, regardless of whether it succeeded or failed.

---

## 11. Geospatial Distance Calculation

### Why Geodesic (Vincenty/Karney) over Haversine

The Earth is not a sphere. It is an oblate spheroid with an equatorial radius of 6,378.137 km and a polar radius of 6,356.752 km — a difference of ~21 km.

| Method | Earth model | Typical accuracy | Use case |
|---|---|---|---|
| Euclidean (flat) | Flat plane | Poor, degrades with distance | Never for geo |
| Haversine | Perfect sphere | ~0.5% error near poles | Rough estimates only |
| Vincenty / Karney (geodesic) | WGS-84 ellipsoid | Millimetre accuracy | Production use |

For an address book where users search in any city worldwide, using Haversine could misclassify addresses near the poles by several kilometres. `geopy.distance.geodesic` uses the WGS-84 ellipsoid model (the same model used by GPS), giving correct results everywhere on Earth.

### Current Implementation Notes

The current implementation fetches all addresses from the database and filters in Python. This is correct for small datasets. For larger datasets, see the Future Scope section (spatial indexing).

---

## 12. Testing Architecture

### Test Isolation Strategy

Each test runs against its own isolated database transaction:

```python
@pytest.fixture()
def db_session() -> Session:
    connection = test_engine.connect()
    transaction = connection.begin()           # open a transaction
    session = TestSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()                     # ← undo all writes after each test
    connection.close()
```

**Why transaction rollback instead of truncating tables?**

Rollback is faster than DELETE/TRUNCATE and fully atomic. Any rows inserted during a test are erased when the test ends, with no risk of partial cleanup. This means tests are completely independent — the order in which they run does not matter.

**Why override `get_db` rather than monkey-patching?**

```python
app.dependency_overrides[get_db] = override_get_db
```

FastAPI's `dependency_overrides` is the official mechanism for substituting dependencies in tests. It does not touch any application code. The service, repository, and routes all continue to run unmodified — the only change is which `Session` instance is injected. This tests the real code paths, not mocked stubs.

### Test Coverage

| Test Class | Cases | What it validates |
|---|---|---|
| `TestCreateAddress` | 4 | 201 on valid input, 422 on invalid lat/lon/missing field |
| `TestGetAddress` | 2 | 200 on existing, 404 on missing |
| `TestUpdateAddress` | 3 | Partial update, 404 on missing, 422 on invalid lat |
| `TestDeleteAddress` | 3 | 204 on success, 404 on missing, 404 on re-access after delete |
| `TestNearbyAddresses` | 4 | Nearby included, distant excluded, 422 on invalid radius/lat |

**Total: 16 test cases covering every functional requirement.**

---

## 13. Design Decisions & Trade-offs

### SQLite over PostgreSQL

**Decision:** Use SQLite for the initial implementation.

**Reasoning:** SQLite requires zero infrastructure setup. The service can be cloned, installed, and running in under 5 minutes with no Docker, no database server, no credentials. The codebase is written in a way that makes swapping to PostgreSQL a one-line change in `.env` (`DATABASE_URL=postgresql://...`).

**Trade-off:** SQLite has limitations for concurrent writes and lacks native geospatial extensions (PostGIS). These are acceptable for the current scope.

### In-Memory Filtering for Nearby Search

**Decision:** Fetch all addresses and filter in Python with geopy.

**Reasoning:** Correct and simple for small datasets. No raw SQL. No database-specific extension required.

**Trade-off:** Does not scale beyond ~100,000 records without degradation. Addressed in Future Scope.

### PATCH over PUT for Updates

**Decision:** Use HTTP PATCH for partial updates.

**Reasoning:** Clients should not need to re-send unchanged data. PATCH with `exclude_unset=True` is the safest and most practical approach.

**Trade-off:** PATCH semantics require careful `exclude_unset=True` handling to avoid overwriting fields with `None`. This is implemented correctly but requires attention when extending `AddressUpdate`.

### No Authentication

**Decision:** No auth in v1.

**Reasoning:** Scope boundary. Authentication is an orthogonal concern that would significantly expand the codebase without demonstrating the core architectural patterns.

**Trade-off:** The API is unauthenticated. Every address is readable and modifiable by any caller. See Future Scope.

---

## 14. SOLID Principles Applied

### Single Responsibility Principle (SRP)

Every class and module has exactly one reason to change:
- `AddressRepository` changes only if the persistence strategy changes.
- `AddressService` changes only if business rules change.
- `address_routes.py` changes only if the HTTP API contract changes.
- `geo.py` changes only if the distance calculation algorithm changes.

### Open/Closed Principle (OCP)

Adding a new resource (e.g., `Contact`) requires creating new files — `models/contact.py`, `schemas/contact.py`, `repositories/contact_repository.py`, etc. — without modifying any existing file. The architecture is open for extension and closed for modification.

### Liskov Substitution Principle (LSP)

`AddressCreate` and `AddressUpdate` do not substitute for each other — they have different contracts deliberately. `AddressResponse` inherits `AddressBase` and extends it (adds `id`, timestamps) without violating the base contract.

### Interface Segregation Principle (ISP)

The service depends on `AddressRepository` — a narrow interface covering only address operations. It does not depend on a god-object database manager. If a second resource is added, it gets its own repository.

### Dependency Inversion Principle (DIP)

The service does not instantiate its repository — it receives it via constructor injection. The route handler does not instantiate the service — it receives it via FastAPI `Depends`. High-level modules (service, routes) depend on abstractions (constructor parameters), not on concrete instantiation.

---

## 15. Security Considerations

### Input Validation

All inputs are validated at the Pydantic layer before reaching the service or database. Coordinate bounds, string lengths, and required fields are enforced by schema constraints, not conditional code.

### No Internal Detail Leakage

All `try/except` blocks log the full exception internally (`exc_info=True`) but expose only a generic, safe message to the API consumer. SQL error messages, table names, column names, and stack traces never appear in HTTP responses.

### SQL Injection Prevention

The service uses the SQLAlchemy ORM exclusively. No raw SQL strings are constructed anywhere in the codebase. SQLAlchemy's query API uses parameterised queries at the driver level, making SQL injection structurally impossible.

### No Hardcoded Credentials

All configuration — including the database URL — is read from environment variables. The repository does not contain a `.env` file (it is `.gitignored`). Credentials are never committed to source control.

---

## 16. Future Scope & Roadmap

### Immediate Next Steps (Production Readiness)

| Item | Priority | Description |
|---|---|---|
| **Alembic Migrations** | High | Replace `create_all()` with versioned schema migrations for safe production deployments |
| **Authentication & Authorization** | High | JWT-based auth (FastAPI + python-jose) or OAuth2 integration. Every endpoint should require a valid token |
| **Pagination** | High | `GET /addresses/nearby/search` should support `limit` and `offset` (or cursor-based pagination) to prevent unbounded responses |
| **PostgreSQL + PostGIS** | Medium | Switch from SQLite to PostgreSQL with the PostGIS extension for native geospatial indexing. The `ST_DWithin` function performs radius queries in the database without loading all records into memory |
| **Spatial Indexing** | Medium | Once on PostGIS, add a `GIST` index on the geometry column for O(log n) radius queries instead of O(n) Python-level filtering |

### Short-Term Improvements

| Item | Description |
|---|---|
| **Structured JSON Logging** | Replace the plain-text log formatter with a JSON formatter (e.g., `python-json-logger`). JSON logs integrate directly with log aggregators (CloudWatch, Datadog, Splunk) without needing custom parsing rules |
| **Request ID / Correlation ID** | Add a middleware that generates a UUID per request and injects it into every log line produced during that request. Essential for tracing a single request across multiple log lines in production |
| **Request/Response Middleware Logging** | A middleware that logs every incoming request (method, path, client IP) and outgoing response (status code, duration) in a single structured log entry |
| **Health Check Enhancement** | Extend `/health` to include a database connectivity check (attempt a lightweight query) and return `{"status": "ok", "database": "ok"}` or `503` if the database is unreachable |
| **Input Sanitisation** | Add stricter validation on string fields — disallow control characters, limit character sets where appropriate |
| **Rate Limiting** | Add per-client rate limiting (e.g., `slowapi`) to prevent abuse of the nearby search endpoint |

### Medium-Term Architecture Evolution

| Item | Description |
|---|---|
| **Async SQLAlchemy** | Convert from synchronous SQLAlchemy to `AsyncSession` with `asyncpg` driver. FastAPI is fully async — synchronous DB calls block the event loop. Async DB access eliminates this bottleneck |
| **Caching Layer** | Add Redis caching for frequently-queried addresses and nearby search results with a short TTL. Reduces database load for read-heavy workloads |
| **Event-Driven Architecture** | Emit domain events (e.g., `AddressCreated`, `AddressDeleted`) to a message queue (SQS, Kafka) to enable downstream consumers (search indexing, audit logging, notifications) without coupling |
| **Full-Text Search** | Integrate Elasticsearch or PostgreSQL full-text search for querying addresses by name, city, or country — complementary to geospatial search |
| **Soft Deletes** | Add a `deleted_at` timestamp column. Instead of physically deleting rows, mark them as deleted. Allows for recovery windows and audit trails |

### Long-Term / Scale

| Item | Description |
|---|---|
| **Horizontal Scaling** | Move from SQLite to a client-server database (PostgreSQL) with a connection pool (PgBouncer). Multiple application instances can share the same database |
| **Read Replicas** | Route read operations (GET, nearby search) to read replicas and write operations to the primary. Dramatically increases read throughput |
| **Containerised Deployment** | The included `Dockerfile` is the starting point. Add `docker-compose.yml` for local development with a PostgreSQL container and a CI/CD pipeline (GitHub Actions) for automated testing and deployment |
| **OpenTelemetry** | Instrument with OpenTelemetry for distributed tracing. Every request gets a trace with spans for each layer (route → service → repository → DB), enabling performance profiling and bottleneck identification |
| **Contract Testing** | Add Schemathesis or Dredd to automatically generate and run tests from the OpenAPI schema, ensuring the documented API contract never drifts from the actual implementation |

---

*This document reflects the state of the service as of version 1.0.0. It should be updated alongside the codebase whenever architectural decisions change.*
