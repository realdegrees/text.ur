<div align="center">

<img src="frontend/src/lib/images/logo/logo_dark.svg" alt="text.ur logo" height="80" />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="frontend/src/lib/images/ur/ur-logo-dark.webp" alt="University of Regensburg" height="80" />

# text.ur

**A self-hosted collaborative PDF annotation platform**

[![CI/CD](https://github.com/realdegrees/text.ur/actions/workflows/ci.yml/badge.svg)](https://github.com/realdegrees/text.ur/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node 20+](https://img.shields.io/badge/Node-20+-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Svelte 5](https://img.shields.io/badge/Svelte-5-FF3E00?logo=svelte&logoColor=white)](https://svelte.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)

</div>

---

text.ur is a self-hosted platform for real-time collaborative PDF annotation, created for the [Institute of German Studies at the University of Regensburg](https://www.uni-regensburg.de/language-literature-culture/german-studies/startseite/index.html) on behalf of [Tatjana Kühnast](https://www.uni-regensburg.de/sprache-literatur-kultur/germanistik-ndl-1/mitarbeitende/tatjana-kuehnast/index.html).  

Users create groups, upload PDF documents, and invite collaborators via share links or email. Group members can then highlight text passages, write threaded comments in Markdown, and tag or filter annotations - with live cursors, presence tracking, and instant updates across all connected clients. The application is designed for on-premises deployment and runs entirely on your own infrastructure.

## ✨ Features

<table>
<tr>
<td width="33%" valign="top">

#### 👥 Groups & Share Links

Create a group, upload documents, and invite collaborators via email or share link. Share links require registration by default but can optionally allow anonymous access through temporary, device-bound guest accounts. Guests can later upgrade to persistent accounts, keeping all groups, comments, and data.

</td>
<td width="33%" valign="top">

#### 🏷️ Tags & Descriptions

Admins can add a per-document description for context and instructions, and define custom, color-coded tags describing the kinds of annotations expected. Tags are assigned to comments for categorization and used as filter criteria.

</td>
<td width="33%" valign="top">

#### 📝 Annotations & Comments

Highlight text in a PDF to create an annotation anchored to that location. Comments support Markdown and threaded replies. Nearby annotations are intelligently grouped to reduce clutter on busy pages.

</td>
</tr>
<tr>
<td width="33%" valign="top">

#### 📡 Real-Time Sync

Comments, replies, tags, online status, and live cursors sync instantly across all clients with no manual refresh.

</td>
<td width="33%" valign="top">

#### 📌 Comment Pinning

Pin comments to keep them at the top of the sidebar regardless of scroll position or active filters. Pins are local per user - everyone organizes their own view.

</td>
<td width="33%" valign="top">

#### 🔍 Comment Filtering

Show or hide comments by tag, author, or any combination. Filters stack to progressively narrow results. Like pins, filters are local per user.

</td>
</tr>
<tr>
<td width="33%" valign="top">

#### 💾 Local Persistence

Comment drafts, pins, and filters persist locally across sessions and reconnects. Lose connection mid-edit? Your text is still there when you come back.

</td>
<td width="33%" valign="top">

#### 👁️ Visibility Controls

Set individual comments to **public**, **restricted** (admins only), or **private** (author only). Admins can also put entire documents into restricted mode where users only see their own comments - ideal for instructor review.

</td>
<td width="33%" valign="top">

#### More

**Fine-grained permissions** - role-based access control with configurable defaults per group

**Self-hosted** - Docker Compose behind a reverse proxy on your own infrastructure

**Multi-language** - English and German out of the box

</td>
</tr>
</table>

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | SvelteKit, Svelte 5, TailwindCSS 4, PDFSlick |
| **Backend** | FastAPI, SQLModel, Pydantic, Alembic |
| **Database** | PostgreSQL 16 |
| **Storage** | MinIO (S3-compatible) |
| **Cache & Pub/Sub** | Redis 8 |
| **Deployment** | Docker Compose, Gunicorn + Uvicorn |

## 🚀 Quick Start

**Prerequisites:** Docker, Python 3.12+, Node.js 20+, pnpm 10

#### 1. Clone and configure

```bash
git clone https://github.com/realdegrees/text.ur.git
cd text.ur
cp .env.template .env
```

Edit `.env` as needed. The template defaults work for local development. For a full description of all variables see the [Environment Variables](docs/deployment.md#-environment-variables) reference.

#### 2. Start infrastructure

```bash
docker compose -f docker-compose.dev.yml up -d
```

This starts PostgreSQL, Redis, MinIO, and MailHog.

#### 3. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd database && alembic upgrade head && cd ..
uvicorn app.main:app --reload --port 8000
```

API docs are available at `http://localhost:8000/api/docs`.

#### 4. Frontend (separate terminal)

```bash
cd frontend
pnpm install
pnpm dev
```

The app is available at `http://localhost:5173`. Captured emails can be viewed at `http://localhost:6026` (MailHog).

> 💡 The repository includes **VS Code launch configurations** for debugging both the backend (debugpy) and frontend (Node + Chrome DevTools). See the [Deployment Guide](docs/deployment.md#-vs-code) for details.

For production deployment, see the [Deployment Guide](docs/deployment.md).

## 📖 Documentation

| | Document | Description |
|---|---|---|
| 🏗️ | [Architecture](docs/architecture.md) | System design, auth flow, WebSocket protocol, access control, type sync pipeline |
| 🚢 | [Deployment](docs/deployment.md) | Dev setup, production deployment, reverse proxy, environment variables |
| ⚙️ | [CI/CD Pipeline](docs/ci.md) | Pipeline stages, path filtering, Docker image tagging, local CI checks |
| 🤝 | [Contributing](docs/contributing.md) | Development workflow, code style, testing, pull requests |
| 🐍 | [Backend](backend/README.md) | Project structure, patterns, models, dependencies, testing |
| 🟠 | [Frontend](frontend/README.md) | Project structure, Svelte 5 runes, API client, generated files, i18n |
| 🗄️ | [Database](backend/database/README.md) | Migrations, initialization, schema |

## 🤝 Contributing

Contributions are welcome. See the [Contributing Guide](docs/contributing.md) for development setup, code style conventions, and how to submit changes.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
