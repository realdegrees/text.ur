# 🤝 Contributing

> [Back to main README](../README.md)

Contributions are welcome, whether it's bug fixes, feature improvements, or documentation updates.

## 🏁 Getting Started

1. Fork the repository and clone your fork.
2. Follow the [Development Setup](deployment.md#-development-setup) guide to get a local environment running.
3. Create a branch from `develop` for your changes.

## 🔄 Development Workflow

1. Make your changes on a feature branch.
2. Run the relevant lint and test commands to verify your changes pass.
3. If you changed backend models, run `pnpm typegen` from the `frontend/` directory and commit the regenerated files.
4. Open a pull request against `develop`.

## 🎨 Code Style

The [CI pipeline](ci.md) runs linting for both backend and frontend on every push and pull request. Refer to the linter configurations for the enforced rules:

- **Backend** - [pyproject.toml](../backend/pyproject.toml) (Ruff)
- **Frontend** - [.prettierrc](../frontend/.prettierrc) (Prettier) and [eslint.config.js](../frontend/eslint.config.js) (ESLint)

## 🧪 Testing

See the [Backend README](../backend/README.md#-testing) and [Frontend README](../frontend/README.md#-testing) for how to run tests.

## 🔗 Type Generation

After any change to Pydantic models in `backend/app/models/`, regenerate the frontend types:

```bash
cd frontend
pnpm typegen
```

This updates `src/api/types.ts` and `src/api/schemas.ts`. Commit these generated files along with your model changes. The CI pipeline will fail if they are out of sync.

## 🗄️ Database Migrations

If your changes modify SQLModel table definitions:

```bash
cd backend/database
alembic revision --autogenerate -m "description of change"
alembic upgrade head
```

Review the generated migration file before committing. The CI validates that migrations are in sync with the models.

> **⚠️ Important:** If a table change requires migration of existing user data (e.g. renaming a column, changing an enum, splitting a field), the auto-generated migration script must be manually modified to handle the transformation. Alembic's autogenerate only detects structural changes - it does not generate data migration logic.

## 📋 Pull Requests

- Branch from `develop`, not `main`.
- Keep changes focused - one feature or fix per PR.
- Include a description of what changed and why.
- Ensure all CI checks pass.
