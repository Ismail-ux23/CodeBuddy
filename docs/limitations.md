# Honest release limitations

The requested architecture and core flows are implemented, but this is a release candidate requiring further acceptance before production use.

## Current review (2026-10-13)

The fresh pre-push review runs in a different environment from the historical checks below.
See [github-readiness.md](github-readiness.md) for the current results. Historical service and
live-provider claims have not been independently rerun in this environment. Docker is unavailable,
and the Playwright browser download failed here. These remain explicit verification limits.

## Historical verification gates

- Local PostgreSQL 18.6 with pgvector 0.8.6 and Redis 7.4.11 now run on isolated loopback ports. The migration and all 71 backend tests passed, including ten real-service integration tests. The default suite replaces Gemini; an explicit live browser test uses the real provider. Real Redis broker delivery now passes in the browser harness. Docker/Compose startup and the broader deletion race matrix remain unverified.
- Live indexing, cited answers, guide generation and Markdown download passed on a synthetic two-line repository with gemini-3.5-flash and gemini-embedding-001. This model replaced gemini-3.8-flash after repeated 503 responses. The user's real repository also completed indexing (400 chunks) after adding rate-limit pacing and retry backoff; three oversized-line CSS files were excluded. Real-repository answer acceptance and broad retrieval/faithfulness metrics remain unmeasured.
- Deployment was requested, but the user has no hosting account yet. No deployment or infrastructure purchase has been performed.

## Scope gaps versus the complete master specification

- Ingestion and generation use one typed jobs table; sessions use Redis rather than PostgreSQL. This is documented in architecture.
- Archive processing is bounded by bytes/entries. There is no separate parser subprocess timeout. Symbol context and guide evidence selection are basic; they do not build call graphs or guarantee diverse architectural coverage.
- Embeddings are not reused across snapshots. Retrying the same snapshot reuses completed embeddings by content hash only when the stored model and dimension match; reindexing a new snapshot still performs new embeddings.
- The source tab strip retains up to eight recently opened files; it is not a full IDE. Panel width preferences are device-local and per-user.
- Upload UI shows genuine pending state, not byte progress. API upload validation is synchronous before the asynchronous parsing/embedding job.
- Guides show a stale-snapshot banner, copy text, and export Markdown. The evidence selector still needs broader evaluation on large repositories.
- Request-specific Pydantic schemas cover auth/project/questions/answers; some small action endpoints use manual validation.
- The OpenAPI file documents paths and common contracts, but does not fully describe every response field.
- Public browser tests cover landing/menu/demo. Private registration→upload→index→chat→guide→download→logout/login passes with both the test provider and live Gemini on a synthetic repository. Broader real-repository acceptance and the full failure/race matrix remain incomplete.
- Live public demo questions are disabled. Password reset/email verification are omitted without a mail provider. Roadmap items (GitHub, teams, graphs, billing, mobile apps) are not exposed as working controls.
- The independent model support check is not proof of faithfulness; manual evaluation remains necessary.

Consult `test-report.md` for checks actually run. Do not equate a successful frontend build or fixture validation with completion of the full definition of done.
