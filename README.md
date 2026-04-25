# Archyve AI

**Team:** Assaf Boneh, Adrian Nica

A RAG-powered document Q&A platform. Upload documents, index them with Gemini embeddings, and chat with your knowledge base.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for the database and full-stack deployment)
- A Gemini API key
- Auth0 app and Cloudflare R2 bucket (for cloud features)

> Use **bash** for all commands below.

## Setup

**1. Copy and fill in environment variables**

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
- `DATABASE_URL` / `DATABASE_URL_DIRECT` — Neon Postgres connection strings
- `GEMINI_API_KEY` — from Google AI Studio
- `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_ISSUER`, `AUTH0_JWKS_URL`
- `NEXT_PUBLIC_AUTH0_DOMAIN`, `NEXT_PUBLIC_AUTH0_CLIENT_ID`, `NEXT_PUBLIC_AUTH0_AUDIENCE`

**2. Install dependencies**

```bash
make install
```

**3. Run database migrations**

```bash
make migrate
```

## Running locally

Start each service in a separate terminal:

```bash
make dev-api       # API server at http://localhost:8000
make dev-worker    # Background indexing worker
make dev-web       # Web app at http://localhost:3000
```

## Testing

```bash
make test
```
