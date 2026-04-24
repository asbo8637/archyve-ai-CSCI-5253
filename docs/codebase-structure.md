# Codebase Structure

This repo is organized by deployable service first and by product feature second.

## Top Level

- `apps/web`: Next.js product UI
- `apps/api`: FastAPI request-time backend
- `apps/worker`: async document processing worker
- `packages/python-common`: shared Python code used by API and worker

## API Layout

Use `apps/api/api_app/features/<feature>` for product logic:

- `router.py`: HTTP routes for that feature
- `service.py`: request-time application logic
- `schemas.py`: API request/response models for that feature
- `constants.py`: feature-local constants only

Current features:

- `system`: health and runtime checks
- `workspace`: bootstrap/workspace context
- `companies`: company bootstrap helpers
- `documents`: uploads and document listing
- `indexing`: indexing job scheduling

Use `apps/api/api_app/integrations` for provider-specific adapters and protocols:

- `auth.py`: WorkOS or session integration
- `storage.py`: local filesystem now, GCS later
- `queue.py`: DB polling now, Pub/Sub later
- `llm.py`: embeddings and answer generation clients
- `telemetry.py`: Sentry, PostHog, Langfuse adapters

When new product areas are added, create them under `features/`:

- `conversations`
- `retrieval`
- `training`
- `feedback`
- `audit`

## Worker Layout

Use `apps/worker/worker_app/jobs` for async pipelines and batch jobs:

- `document_indexing.py`: normal ingestion pipeline
- `document_reindexing.py`: future bulk reindex job entrypoint

Use `apps/worker/worker_app/integrations` for external adapters such as embeddings,
queue consumption, and storage resolution.

## Shared Python Layout

Only place code in `packages/python-common/archyve_common` if it is truly shared
between services:

- database session and metadata
- SQLAlchemy models
- shared message contracts
- shared indexing helpers
- shared base settings

Do not put API-only route schemas or worker-only orchestration code there.
