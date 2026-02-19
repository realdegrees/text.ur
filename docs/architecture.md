# 🏗️ Architecture

> [Back to main README](../README.md)

This document describes the system architecture of text.ur, covering service topology, request flow, authentication, real-time events, access control, and the type synchronization pipeline.

## Table of Contents

- [🧩 Service Topology](#-service-topology)
- [🔀 Request Flow](#-request-flow)
- [🔐 Authentication](#-authentication)
- [📡 Real-Time Events (WebSocket)](#-real-time-events-websocket)
- [🛡️ Access Control](#️-access-control)
- [🔑 Permission Model](#-permission-model)
- [🔗 Type Synchronization Pipeline](#-type-synchronization-pipeline)
- [🗄️ Database Schema](#️-database-schema)

---

## 🧩 Service Topology

| Service | Role | Technology |
|---|---|---|
| **Frontend** | SSR application server, static asset serving, SSR API proxy | SvelteKit on Node.js (port 3000) |
| **Backend** | REST API, WebSocket server, business logic | FastAPI on Gunicorn + Uvicorn (port 8000) |
| **PostgreSQL** | Primary data store | PostgreSQL 16 |
| **PgBouncer** | Connection pooling (transaction mode, optional) | PgBouncer 1.24 |
| **MinIO** | S3-compatible object storage for PDF files | MinIO |
| **Redis** | Pub/sub for WebSocket events, rate limiting backend | Redis 8 |
| **Watchtower** | Automatic container restarts on new image push | Watchtower (production only) |
| **MailHog** | Mock SMTP server for email testing | MailHog (development only) |

---

## 🔀 Request Flow

text.ur uses a **hybrid request model**. The browser communicates with both the frontend and the backend, depending on the context.

### Two Base URLs

| Variable | Used By | Example |
|---|---|---|
| `INTERNAL_BACKEND_BASEURL` | SvelteKit server (private) | `http://backend:8000` (Docker) |
| `PUBLIC_BACKEND_BASEURL` | Browser (public, embedded in client bundle) | `https://api.example.com` |

In development both typically point to `http://localhost:8000`.

### Request Types

```
Browser
  │
  ├── Page loads ──────────► SvelteKit (port 3000) ──► SSR rendering
  │                              │
  │                              │ handleFetch rewrites /api/* to
  │                              │ INTERNAL_BACKEND_BASEURL
  │                              ▼
  │                          FastAPI (port 8000)
  │
  ├── Client-side API ─────► FastAPI (port 8000)  [direct, via PUBLIC_BACKEND_BASEURL]
  │
  └── WebSocket ───────────► FastAPI (port 8000)  [direct, via PUBLIC_BACKEND_BASEURL]
```

| Request Type | Path | Target |
|---|---|---|
| SSR page loads | Server-side `fetch()` during rendering | Proxied through SvelteKit to backend via `INTERNAL_BACKEND_BASEURL` |
| Client-side API calls | `ApiClient` in the browser | Direct to backend via `PUBLIC_BACKEND_BASEURL` |
| WebSocket connections | `ws(s)://` from the browser | Direct to backend via `PUBLIC_BACKEND_BASEURL` |

### SSR Proxy (Server-Side Only)

During server-side rendering, SvelteKit's `handleFetch` hook in `hooks.server.ts` intercepts `/api/*` requests:

1. Rewrites the URL from `PUBLIC_BACKEND_BASEURL` to `INTERNAL_BACKEND_BASEURL` (e.g. Docker-internal hostname).
2. Forwards `access_token` and `refresh_token` cookies from the browser request to the backend.
3. If the backend returns `401`, transparently attempts a token refresh and retries the original request.
4. Forwards `Set-Cookie` headers from backend responses back to the browser.

### Client-Side Requests (Browser)

After the initial page load, all subsequent API calls go **directly from the browser to the backend**:

1. The `ApiClient` singleton resolves all paths against `PUBLIC_BACKEND_BASEURL`.
2. Cookies are sent via `credentials: 'include'`.
3. The `ApiClient` has its own 401/refresh logic - if the backend returns 401, it calls `/api/login/refresh` directly, then retries.

### WebSocket Connections

WebSocket connections are established **directly from the browser to the backend**, bypassing SvelteKit entirely. The URL is constructed from `PUBLIC_BACKEND_BASEURL` with the protocol switched to `ws://` or `wss://`. Authentication uses the same HTTP-only cookies sent automatically with the WebSocket upgrade request.

---

## 🔐 Authentication

### Token Architecture

text.ur uses a **nested JWT** strategy:

1. **Inner token** - signed with the user's personal `secret` field (stored in the `User` table). This allows per-user token invalidation by rotating the secret.
2. **Outer token** - the inner token is embedded as a claim in an outer JWT signed with the global `JWT_SECRET`. This allows the backend to identify the user from the outer token, load their secret, and then verify the inner token.

### Token Lifecycle

| Token | Storage | Default Expiry | Purpose |
|---|---|---|---|
| `access_token` | HTTP-only secure cookie | 720 minutes (12h) | Authenticates API requests |
| `refresh_token` | HTTP-only secure cookie | 3 days (30 days for guests) | Obtains new access tokens |

### Cookie Configuration

| Setting | Default | Description |
|---|---|---|
| `COOKIE_SECURE` | `True` | Cookies only sent over HTTPS |
| `COOKIE_SAMESITE` | `lax` | Cookies sent on same-site requests and top-level navigations |
| `httponly` | `True` | Cookies inaccessible to JavaScript |

### Auth Flows

- **Registration** - User submits credentials, receives a signed email verification link. Clicking the link verifies the account. `DEBUG_ALLOW_REGISTRATION_WITHOUT_EMAIL` bypasses this in development.
- **Anonymous/Guest Access** - Share links with `allow_anonymous_access` enabled create temporary guest accounts with auto-generated credentials. Guest accounts can later upgrade to full accounts by providing email and password.
- **Login** - Credentials validated via bcrypt, JWT pair issued as cookies. Rate limited to 5 requests per minute.
- **Token Refresh** - Implemented in two places: server-side in `handleFetch` (for SSR requests) and client-side in `ApiClient` (for browser requests). Both intercept 401 responses, call `/api/login/refresh`, and retry. Expired sharelink-based memberships are cleaned up during refresh.
- **Logout** - Clears cookies. "Logout all devices" rotates the user's `secret` field, invalidating all existing tokens globally.
- **Password Reset** - Generates a presigned URL sent via email. The link includes a hash of the current password, making it single-use (changing the password invalidates the link).

---

## 📡 Real-Time Events (WebSocket)

### Connection Lifecycle

1. Browser opens a WebSocket connection directly to the backend at `/api/documents/{id}/events/comments`.
2. Server authenticates via `BasicAuthentication` (supports anonymous/guest users) using HTTP-only cookies.
3. Server sends a `handshake` event containing the list of currently active users.
4. Client sends a `heartbeat` every 3 minutes. Users are considered disconnected after 4 minutes without a heartbeat.
5. On disconnect, a `user_disconnected` event is broadcast.

### Event Types

| Event | Direction | Description |
|---|---|---|
| `handshake` | Server → Client | Initial payload with active users |
| `user_connected` | Server → Clients | A new user joined the document |
| `user_disconnected` | Server → Clients | A user left the document |
| `create` | Bidirectional | Comment created |
| `update` | Bidirectional | Comment updated |
| `delete` | Bidirectional | Comment deleted |
| `view_mode_changed` | Server → Clients | Document view mode changed |
| `mouse_position` | Bidirectional | Cursor position broadcast |

### Cross-Instance Support

WebSocket events are broadcast via **Redis pub/sub**, allowing multiple backend instances to relay events to all connected clients regardless of which instance holds their WebSocket connection.

Each WebSocket connection has a unique `connection_id`. Outgoing events include this ID so the originating client can ignore its own echoed events.

### Visibility Filtering

The `transform_outgoing` hook on the events router applies the same access control rules as the REST API. Comment events are filtered based on the receiving user's permissions, the document's view mode, and the comment's visibility level. Users only receive events for comments they are allowed to see.

### Event Router Factory

Event routers are created using the `get_events_router()` factory pattern, which accepts hooks for `transform_outgoing` (visibility filtering) and `handle_incoming` (event enrichment). This allows reuse across different resource types.

---

## 🛡️ Access Control

### Guard System

Access control is implemented via the `EndpointGuard[T]` class in `util/queries.py`. Each guard encapsulates:

- **SQL WHERE clause** - applied at the database query level to filter results the user is allowed to see.
- **Python predicate** - applied after loading to perform fine-grained checks that cannot be expressed in SQL.

Guards can be combined with AND/OR logic. The available guards are:

| Guard | Purpose |
|---|---|
| `Guard.document_access()` | Controls which documents a user can see based on group membership and document visibility |
| `Guard.comment_access()` | Controls comment visibility based on user permissions, document view mode, and comment visibility level |
| `Guard.group_access()` | Controls group visibility based on membership |
| `Guard.sharelink_access()` | Controls share link visibility (author or group admin) |
| `Guard.is_account_owner()` | Ensures the user can only modify their own account |
| `Guard.must_share_group()` | Ensures two resources belong to the same group |
| `Guard.reaction_access()` | Controls reaction visibility based on comment access (not yet fully implemented) |

### Comment Visibility

Comment visibility depends on the interaction of three factors:

1. **Comment visibility level**: `private`, `restricted`, or `public`
2. **Document view mode**: `restricted` or `public`
3. **User permissions**: particularly `view_restricted_comments` and `administrator`

When the document is in `restricted` view mode, only the comment author and users with `view_restricted_comments` or `administrator` permissions can see any comments. When in `public` mode, visibility follows the comment's own visibility level.

---

## 🔑 Permission Model

Permissions are stored as an array of strings on the `Membership` table. There are 13 permissions organized by category:

| Category | Permissions |
|---|---|
| **Administration** | `administrator` |
| **Comments** | `add_comments`, `remove_comments`, `view_restricted_comments` |
| **Members** | `add_members`, `remove_members`, `manage_permissions` |
| **Documents** | `upload_documents`, `view_restricted_documents`, `delete_documents` |
| **Reactions** | `add_reactions`, `remove_reactions` (not yet fully implemented) |
| **Tags** | `manage_tags` |

### Permission Hierarchy

- **Group owner** has all permissions implicitly and cannot be restricted.
- **Administrators** have all permissions except ownership transfer.
- **Regular members** have permissions assigned explicitly.
- Permissions cannot be removed if they are part of the group's `default_permissions` or the member's originating share link permissions.

---

## 🔗 Type Synchronization Pipeline

text.ur maintains end-to-end type safety from the database to the frontend. Changes to backend Pydantic models automatically propagate to frontend TypeScript types and Zod validation schemas.

```
Pydantic models (backend)
        │
        │  pydantic2ts
        ▼
TypeScript interfaces (frontend/src/api/types.ts)   ← DO NOT EDIT
        │
        │  ts-to-zod
        ▼
Zod schemas (frontend/src/api/schemas.ts)            ← DO NOT EDIT
```

**Workflow:**

1. Modify Pydantic models in `backend/app/models/`.
2. Run `pnpm typegen` from the frontend directory.
3. Commit the regenerated `types.ts` and `schemas.ts`.

The CI pipeline validates this by running `pnpm typegen` and checking for uncommitted diffs. If the generated files don't match what's committed, the pipeline fails.

An additional generated file, `frontend/src/api/maps.generated.ts`, contains field exclusion maps produced by `backend/scripts/generate_exclusion_maps.py`.

---

## 🗄️ Database Schema

The database uses 9 tables managed by SQLModel (SQLAlchemy) with Alembic migrations:

| Table | Primary Key | Description |
|---|---|---|
| `User` | `id` (int, auto) | Accounts with optional email/password, guest support, per-user JWT secret |
| `Group` | `id` (string, nanoid) | Collaboration groups with default permissions |
| `Membership` | `(user_id, group_id)` | Group membership with permissions array, owner flag, share link reference |
| `Document` | `id` (string, nanoid) | PDF documents with S3 key, visibility, view mode |
| `Comment` | `id` (int, auto) | Threaded comments with visibility, annotation data (JSONB), Markdown content |
| `Tag` | `id` (int, auto) | Color-coded document-level tags |
| `CommentTag` | `(comment_id, tag_id)` | Ordered many-to-many between comments and tags |
| `Reaction` | `(user_id, comment_id)` | Reactions on comments (not yet fully implemented) |
| `ShareLink` | `id` (int, auto) | Token-based group invitation links with expiry and permission assignment |

The full entity-relationship diagram is available as PlantUML at [`schema.puml`](schema.puml) and as a rendered image in the [Database README](../backend/database/README.md).
