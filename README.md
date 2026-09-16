# GraphLab Academy

GraphLab Academy is an invitation-only learning and practice platform for ontology engineering and Apache Spark. It combines original, source-linked lessons with browser workspaces, trusted grading, staged hints, progress reviews, and capstone projects.

## What is included

- A complete 16-module ontology engineering track: RDF, SPARQL, OWL, SHACL, integration, ingestion, operations, query performance, and governance.
- Four initial PySpark and Spark SQL modules.
- 80 lessons and 180 versioned exercise packages, including guided, independent, and checkpoint modes.
- Three ontology capstone definitions and planned-track templates for data engineering, SQL, and statistics.
- A Next.js learner interface, FastAPI API, PostgreSQL persistence, Redis/Celery jobs, and Docker-based isolated execution.

## Local development

This project is designed to run on a Linux execution host. Copy `.env.example` to `.env`, provide real secrets and OIDC settings, then build the runtime images and start the stack with Docker Compose.

For local runtime verification only, set `SANDBOX_RUNTIME=runc`. A deployed worker must use gVisor's `runsc` runtime. The worker needs access to Docker solely to create short-lived learner sandboxes; the API and web services do not receive that socket.

```powershell
Copy-Item .env.example .env
docker build -f runtimes/java/Dockerfile -t graphlab-jena:1 .
docker tag graphlab-jena:1 graphlab-owl:1
docker build -f runtimes/spark/Dockerfile -t graphlab-spark:1 .
docker compose up --build
```

## Verification

```powershell
.venv\Scripts\python.exe scripts\validate_content.py
.venv\Scripts\python.exe -m pytest api/tests -q
Set-Location web; pnpm exec tsc --noEmit
```

`scripts/verify_runtimes.py` runs selected reference and deliberate wrong solutions in fresh sandboxes. It is intended for the runtime compatibility gate, not the normal authoring loop.

## Release gates

Before a group release, use the checks in [docs/OPERATIONS.md](docs/OPERATIONS.md): validate all content versions, benchmark the runtime limits, verify gVisor isolation on the deployment host, rehearse worker recovery and backup restoration, and pilot with three to five learners.
