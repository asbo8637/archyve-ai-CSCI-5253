# Archyve AI Local Bootstrap

This repo now contains the local Neon-first backend scaffold from the updated plan:

- `apps/web`: Next.js dashboard for uploads and document status
- `apps/api`: FastAPI service for uploads, bootstrap context, and document listing
- `apps/worker`: Python worker that polls the shared `jobs` table for pending work
- `packages/python-common`: shared settings, SQLAlchemy models, message contracts, and text extraction/chunking logic
- `compose.yml`: local API + worker containers pointed at Neon through `.env`

The codebase is organized by service first and by feature second. Feature logic
now lives under `api_app/features`, provider-specific adapters live under
`api_app/integrations`, and async worker entrypoints live under
`worker_app/jobs`. See `docs/codebase-structure.md` for the detailed layout.

## What Step 1 Covers

The goal of this stage is to prove the ingestion loop locally before any cloud setup:

1. Upload a file from the web app
2. Save the raw file locally
3. Create a document row and an indexing job in Postgres
4. Have the worker claim the job and chunk the extracted text
5. Mark the document as `ready`

This stage uses Neon as the system of record. It is still local-first in the sense that
the API and worker run locally, but the database is no longer a local Docker container.

## Current Local Architecture

- Web runs on the host at `http://localhost:3000`
- API can run on the host or in Docker at `http://localhost:8000`
- Neon PostgreSQL is the database backend
- Worker can run on the host or in Docker and polls the `jobs` table
- Files are stored under `./local-data/storage`

Supported extraction in this bootstrap:

- `.txt`
- `.md`
- `.pdf`
- `.docx`
- `.csv`
- `.json`

## Local Setup

Install the repo dependencies:

```bash
make install
```

Run migrations against Neon:

```bash
make migrate
```

Start the API locally:

```bash
make dev-api
```

In a second terminal, start the worker:

```bash
make dev-worker
```

In a third terminal, run the web app:

```bash
make dev-web
```

Then open `http://localhost:3000`.

## Useful Commands

Run tests:

```bash
make test
```

Watch containerized backend logs:

```bash
make logs
```

Run the API + worker in Docker against Neon instead:

```bash
make up
```

Stop the containerized stack:

```bash
make down
```

## What Still Happens Later

This repo is ready for the next infrastructure steps, but these are intentionally deferred:

- signed upload URLs instead of direct API uploads
- real cloud object storage
- a managed queue instead of DB polling
- embeddings and retrieval
- auth and tenant-aware access control
- cloud deployment and secret management
