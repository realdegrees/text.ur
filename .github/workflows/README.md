# CI/CD Pipeline Documentation

This project uses GitHub Actions for continuous integration and deployment. The workflows are organized into separate files matching the original GitLab CI structure.

## Workflows

### 1. Lint (`.github/workflows/lint.yml`)

**Triggers:**
- Pull requests to `main` or `develop` branches (when backend or frontend code changes)
- Push to `develop` branch

**Jobs:**
- `ruff`: Lints Python code in the backend using Ruff
- `eslint`: Lints JavaScript/TypeScript code in the frontend using ESLint

### 2. Validate (`.github/workflows/validate.yml`)

**Triggers:**
- Pull requests to `main` or `develop` branches (when models or database files change)
- Push to `develop` branch (when models or database files change)

**Jobs:**
- `migrations`: Validates that Alembic migration scripts are in sync with database models
- `zod-types`: Validates that generated TypeScript types and Zod schemas are up to date

### 3. Tests (`.github/workflows/tests.yml`)

**Triggers:**
- Pull requests to `main` or `develop` branches (when backend or frontend files change)
- Push to `develop` branch

**Jobs:**
- `pytest`: Runs Python tests with coverage reporting
- `vitest`: Runs frontend tests with coverage reporting

### 4. Build (`.github/workflows/build.yml`)

**Triggers:**
- Pull requests to `main` or `develop` branches (when frontend files change)
- Push to `develop` branch

**Jobs:**
- `frontend`: Builds the frontend application to verify it compiles successfully

### 5. Dockerize (`.github/workflows/dockerize.yml`)

**Triggers:**
- Push to `main` branch (builds with `stable` tag)
- Push to `develop` branch (builds with `latest` tag)

**Jobs:**
- `dockerize-backend`: Builds and pushes backend Docker image to GitHub Container Registry
- `dockerize-frontend`: Builds and pushes frontend Docker image to GitHub Container Registry

## Container Images

Docker images are automatically pushed to GitHub Container Registry (ghcr.io) with the following tags:

**Development (develop branch):**
- `ghcr.io/realdegrees/text.ur/backend:latest` - Latest development backend image
- `ghcr.io/realdegrees/text.ur/backend:<sha>` - Backend image tagged with commit SHA
- `ghcr.io/realdegrees/text.ur/frontend:latest` - Latest development frontend image
- `ghcr.io/realdegrees/text.ur/frontend:<sha>` - Frontend image tagged with commit SHA

**Production (main branch):**
- `ghcr.io/realdegrees/text.ur/backend:stable` - Stable production backend image
- `ghcr.io/realdegrees/text.ur/backend:<sha>` - Backend image tagged with commit SHA
- `ghcr.io/realdegrees/text.ur/frontend:stable` - Stable production frontend image
- `ghcr.io/realdegrees/text.ur/frontend:<sha>` - Frontend image tagged with commit SHA