# 🔄 CI/CD Pipeline

> [Back to main README](../README.md)

The CI/CD pipeline is defined in a single workflow file at [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). It runs on every push and pull request to the `main` and `develop` branches.

## 📑 Table of Contents

- [📋 Pipeline Overview](#-pipeline-overview)
- [🔍 Stage 1: Detect Changes](#-stage-1-detect-changes)
- [🧹 Stage 2: Linting](#-stage-2-linting)
- [✅ Stage 3: Validation](#-stage-3-validation)
- [🏗️ Stage 4: Build](#️-stage-4-build)
- [🧪 Stage 5: Tests](#-stage-5-tests)
- [🐳 Stage 6: Dockerize](#-stage-6-dockerize)
- [🏷️ Docker Image Tags](#️-docker-image-tags)
- [💻 Running CI Checks Locally](#-running-ci-checks-locally)

---

## 📋 Pipeline Overview

The pipeline is organized into 6 sequential stages. Each stage depends on the previous one, but individual jobs within a stage can run in parallel. Jobs are skipped when their relevant files haven't changed (except on `main`, where all jobs always run).

---

## 🔍 Stage 1: Detect Changes

**Job**: `changes`

Uses [dorny/paths-filter](https://github.com/dorny/paths-filter) to determine which parts of the codebase have changed. This allows subsequent jobs to skip unnecessary work.

| Output | Trigger Paths |
|---|---|
| `backend` | `backend/**` |
| `frontend` | `frontend/**` |
| `models` | `backend/app/models/**`, `backend/database/**` |

On pushes to `main`, all jobs run regardless of changes to ensure the stable branch is always fully validated.

---

## 🧹 Stage 2: Linting

### Lint Backend (Ruff)

**Job**: `lint-backend`
**Runs when**: Backend files changed or push to `main`

Installs Ruff 0.15.1 and runs `ruff check .` against the backend code. Ruff enforces the project's Python style rules defined in `pyproject.toml` (line length 80, isort, type annotations, docstrings, etc.).

### Lint Frontend (ESLint + Prettier)

**Job**: `lint-frontend`
**Runs when**: Frontend files changed or push to `main`

Runs `pnpm lint` which executes both Prettier formatting checks and ESLint rules. Uses pnpm 10 and Node 25.

---

## ✅ Stage 3: Validation

### Validate Migrations

**Job**: `validate-migrations`
**Runs when**: Model or database files changed
**Depends on**: `lint-backend`
**Services**: PostgreSQL 16

Verifies that Alembic migration files are in sync with the SQLModel table definitions:

1. Stamps the database at `base` and upgrades to `head` to apply all existing migrations.
2. Runs `alembic revision --autogenerate` to detect any unapplied schema changes.
3. Checks the generated revision file for `op.` calls -- if any exist, it means the models have diverged from the migrations.

**If this job fails**: Run `alembic revision --autogenerate -m "description"` locally from `backend/database/`, review the generated migration, and commit it.

### Validate Types

**Job**: `validate-types`
**Runs when**: Model files changed
**Depends on**: `lint-backend`, `lint-frontend`

Verifies that the generated TypeScript types and Zod schemas are up to date:

1. Installs both Python and Node dependencies.
2. Runs `pnpm typegen` to regenerate `types.ts` and `schemas.ts`.
3. Checks `git status` for uncommitted changes to `*api.ts` files.

**If this job fails**: Run `pnpm typegen` from the `frontend/` directory, review the changes, and commit the regenerated files.

---

## 🏗️ Stage 4: Build

### Build Frontend

**Job**: `build-frontend`
**Runs when**: Frontend files changed
**Depends on**: `lint-frontend`, `validate-types`

Runs `pnpm build` to verify the SvelteKit application compiles successfully. This catches TypeScript errors, missing imports, and SSR compatibility issues that may not surface during development.

---

## 🧪 Stage 5: Tests

### Test Backend (pytest)

**Job**: `test-backend`
**Runs when**: Backend files changed
**Depends on**: `lint-backend`, `validate-migrations`
**Services**: PostgreSQL 16, MinIO

Runs `pytest --cov=app --cov-report=html:coverage --cov-report=term` with full service dependencies. The test database is auto-created by `conftest.py`. Coverage reports are uploaded as artifacts (retained for 7 days).

### Test Frontend (vitest)

**Job**: `test-frontend`
**Runs when**: Frontend files changed
**Depends on**: `lint-frontend`, `build-frontend`

Runs `pnpm test:coverage` using vitest. Coverage reports are uploaded as artifacts (retained for 7 days).

---

## 🐳 Stage 6: Dockerize

**Runs when**: Push to `main` or `develop` only (not on pull requests)
**Depends on**: All previous stages for the respective component

Builds Docker images and pushes them to the GitHub Container Registry (GHCR):

- **Backend**: `ghcr.io/realdegrees/text.ur/backend`
- **Frontend**: `ghcr.io/realdegrees/text.ur/frontend`

Uses Docker Buildx with GitHub Actions cache (`type=gha`) for faster builds.

---

## 🏷️ Docker Image Tags

| Branch | Tags Applied |
|---|---|
| `develop` | `latest`, `sha-<short-commit>` |
| `main` | `stable`, `sha-<short-commit>` |

- Use `stable` for production deployments.
- Use `latest` for staging or development environments tracking the `develop` branch.
- Use `sha-<commit>` to pin a specific version.

In production, [Watchtower](deployment.md#watchtower-auto-updates) can automatically pull new images and restart containers.