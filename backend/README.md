# ⚙️ Backend

> [Back to main README](../README.md)

FastAPI application (Python 3.12+) providing a REST API and WebSocket server. Uses SQLModel for database access, Pydantic for validation, and Alembic for migrations. Linting and formatting are handled by Ruff (see [`pyproject.toml`](pyproject.toml)).

## 🛠️ Commands

All commands assume the virtualenv is activated and are run from `backend/`.

| Task | Command |
|---|---|
| **Run dev server** | `uvicorn app.main:app --reload --port 8000` |
| **Run all tests** | `pytest` |
| **Run single test** | `pytest tests/app/test_document_access.py` |
| **Test with coverage** | `pytest --cov=app --cov-report=html` |
| **Lint** | `ruff check .` |
| **Format** | `ruff format .` |
| **Create migration** | `cd database && alembic revision --autogenerate -m "description"` |
| **Apply migrations** | `cd database && alembic upgrade head` |

---

## 🧩 Key Patterns

### Custom APIRouter

Always use `util.api_router.APIRouter` instead of `fastapi.APIRouter`. The custom router auto-registers trailing-slash variants for all routes so clients don't get 307 redirects.

```python
from util.api_router import APIRouter

router = APIRouter(prefix="/example", tags=["Example"])
```

### Error Handling

All route errors must use `AppException` from `core/app_exception.py` with a code from the `AppErrorCode` enum. Do not raise bare `HTTPException`.

```python
raise AppException(
    status_code=404,
    error_code=AppErrorCode.MEMBERSHIP_NOT_FOUND,
    detail="User is not a member of this group."
)
```

### Resource Dependencies

**`Resource()`** loads a single item by path parameter with access control:

```python
@router.get("/{document_id}")
async def get_document(
    document: Document = Resource(guard=Guard.document_access()),
) -> DocumentRead: ...
```

**`PaginatedResource()`** handles list endpoints with filtering, sorting, and pagination:

```python
@router.get("/")
async def list_documents(
    result: Paginated[DocumentRead] = PaginatedResource(
        guard=Guard.document_access(),
        filter_model=DocumentFilter,
    ),
) -> Paginated[DocumentRead]: ...
```

### Guard System

Guards combine SQL WHERE clauses with Python predicates for access control. They can be composed with `&` (AND) and `|` (OR). See [Architecture: Access Control](../docs/architecture.md#️-access-control) for the full list of guards and how comment/document visibility works.

### Event Router Factory

WebSocket event routers are created with `get_events_router()`, which accepts hooks for outgoing visibility filtering and incoming event enrichment:

```python
events_router = get_events_router(
    model=Comment,
    read_model=CommentRead,
    event_model=CommentEvent,
    transform_outgoing=filter_by_visibility,
    handle_incoming=enrich_comment_event,
)
```

---

## 📦 Models

### Table Models

All database tables inherit from `BaseModel` (`models/base.py`) which provides `created_at` and `updated_at` timestamps. Tables are defined in `models/tables.py` using SQLModel.

### Request/Response Schemas

Each resource has separate Pydantic models: `*Create` (request body for creation), `*Read` (response), `*Update` (partial update). These live in per-resource files under `models/` (e.g. `document.py`, `comment.py`).

### Type Sync

Pydantic models are the source of truth for the frontend type system. After modifying models, run `pnpm typegen` from the frontend directory. See [Architecture: Type Synchronization Pipeline](../docs/architecture.md#-type-synchronization-pipeline).

---

## 🧪 Testing

Tests are in `tests/app/` and use pytest with `asyncio_mode = auto`. The `conftest.py` fixture automatically creates a separate `test` database - do not create it manually.

Factory Boy factories in `tests/factories/models.py` generate test data:

```python
from tests.factories.models import UserFactory, GroupFactory

user = UserFactory()
group = GroupFactory()
```
