# Architecture and interview discussion

## Request path

Browser → Nginx → Next.js pages or Flask `/api/v1`. Flask owns authentication, project access, source storage, and AI orchestration. PostgreSQL owns authoritative state. Redis holds expiring server sessions and transports Celery tasks. It is not the only record of a job. Browser storage is used only for per-user panel width.

## Ingestion

An authenticated upload is read into bounded memory. ZIP metadata is checked before member reads: traversal, absolute/drive paths, Unicode/case collisions, encryption, entry/expansion limits, and compression ratio. Links and special files are excluded before any member reads, including .gitignore reads, and appear in the exclusion report. Link targets are never followed. Nested archive entries are also excluded and reported without opening or recursively extracting them. Supported members are decoded, scanned, redacted while retaining newlines, and saved under generated UUID storage keys outside the web root. Original archives are not persisted. Preview paths do not become filesystem destinations.

A pending snapshot and exclusion report are created. The user can inspect sanitized text and exclude additional files. Only consented indexing creates a provider-bound job. Workers parse functions/module sections with Tree-sitter, fall back to bounded line windows, store inclusive offsets, and embed in batches of 16. Exact cosine search avoids HNSW filtered-recall tradeoffs at this scale. Active snapshot switches in the same transaction that marks the job completed. Failure leaves the previous active snapshot intact.

## Queue consistency

A job and an outbox row are committed together. Beat retries queued outbox dispatches, including broker failure. A per-job PostgreSQL advisory lock serializes duplicate deliveries. Ingestion retries rebuild pending chunks, and a completed job is a no-op. Worker checkpoints persist stage/counts and inspect cancellation. Final commits lock and recheck the project, preventing deletion from resurrecting results. Deletion marks the project first, cancels jobs, removes private files, and cascades database records.

The initial schema consolidates ingestion and generation into `generation_jobs(kind=ingestion|answer|guide)` rather than separate almost-identical tables. Server sessions use Redis TTL rather than a PostgreSQL sessions table. These are explicit deviations from the proposed table names, not missing persistence. The active snapshot has a real deferred-creation foreign key.

## Retrieval

A ready snapshot is authorized before retrieval. Query embeddings must match the snapshot model/dimension. Three candidate branches are snapshot-filtered: cosine vector distance, PostgreSQL `simple` full-text ranking, and exact symbol/path matches. Reciprocal rank fusion sums `1/(60+rank)`. A bounded context chooses up to ten chunks, avoiding completely covered ranges. Prior user questions help follow-up retrieval; prior assistant prose is never source evidence.

A character-based token estimate is conservative only approximately. No universal similarity score is presented as confidence. The guide evidence selector prioritizes README then file order; richer route/manifest diversity selection remains an improvement.

## Grounding

The provider receives untrusted evidence labeled with server-issued chunk IDs. Its structured answer distinguishes observed, inferred, and general claims. Pydantic validates shape. Unknown IDs and claims without required sources are removed, with one retry. The server resolves citations to immutable file/snapshot/ranges. A separate model pass filters claims for support; it is a heuristic and can be wrong. No model output is executed or allowed to fetch external URLs. Markdown raw HTML and images are disabled.

SSE sends stages, not provisional answer tokens. Only completed, validated structures become assistant messages. Regeneration links a new answer to the old one. Guides preserve snapshot identity and export source paths and line ranges.

## Tradeoffs

- Exact vector search is simple and predictable for bounded repositories; larger deployments need measured approximate-index tuning.
- Pattern-based scanning reduces accidental secret exposure but cannot guarantee removal. User review is essential.
- File text is private filesystem storage, while chunks/vectors and ownership are in PostgreSQL; backups must preserve both.
- Synchronous bounded SSE connections work with threaded Gunicorn. A larger deployment should use an event gateway or async service after measuring demand.
- Cancellation is cooperative. An already-issued Gemini request can still be billed.
- PostgreSQL/Redis integration and provider smoke tests are required before calling this production-ready.
