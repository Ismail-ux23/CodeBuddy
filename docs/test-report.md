> Historical implementation report. For the fresh 2026-10-13 pre-push review, see [github-readiness.md](github-readiness.md). Results below describe earlier environments.

# Verification report — 8 October 2026

This report distinguishes local verification from external-service acceptance.

## Passed locally

| Check | Actual result |
|---|---|
| Next.js production build | Passed; all 12 listed routes built |
| TypeScript | `npm run lint` passed |
| Public browser suite | 12 passed with the 4K video, including cursor-following behavior |
| Frontend unit tests | 7 passed with Vitest 5.0.3 |
| Backend pytest | 82 passed, including 14 PostgreSQL/Redis integration tests |
| Python lint | `ruff check app tests --select F` passed |
| Python syntax | `compileall` passed |
| Frozen Python install | `uv sync --frozen --offline --group dev` passed after initial install |
| Alembic offline SQL generation | Passed; generated 255 lines of PostgreSQL schema SQL |
| Flask startup/public smoke | App factory loaded 34 route rules; liveness and three demo endpoints returned 200 with test rate limiting disabled |
| Demo fixture | 7 files; ZIP matches source; all 11 citation ranges valid |
| Evaluation labels | 24 cases, 6 abstentions; all labeled source ranges valid |
| npm audit | Zero known vulnerabilities after updating the test runner |

Backend unit coverage includes traversal/drive/absolute/Unicode paths, duplicate paths, links, nested archives, compression bombs, quotas, malformed ZIPs, common credential masking, examples, exclusion patterns, binary/UTF-8 behavior, parser ranges/fallback, citation removal/ranges, RRF, embedding shape/normalization, and public fixture routes.

The public Chrome browser suite covers six required sizes (390×844, 768×1024, 1024×768, 1440×900, 1920×1080, 1280×600), no horizontal overflow, no normal desktop landing scroll, black body, keyboard menu close/focus restoration, reduced-motion visibility, demo citation highlighting, ambient animation preferences, and hero video playback/pause. The complete public suite passed 11/11 checks with the initial video. The optimized MP4 is additionally checked in the user’s in-app browser.

Screenshots in `docs/screenshots/` were generated from real browser runs. Desktop/mobile landing and demo screenshots were visually inspected. Source text is read-only and the demo citation highlighted exactly four lines (16–19).

## Not run / not measured

- Docker-based PostgreSQL 17 environment: not run. Local PostgreSQL 18.6 / pgvector 0.8.6 / Redis 7.4.11 migration and all 53 backend tests now pass, including the seven integration tests. Pipeline tests use an explicit test-only Gemini double. The run exposed and fixed an integer-versus-timedelta CSRF timeout error.
- Live synthetic browser acceptance now passes. Real FYP ZIP acceptance remains to be verified.
- Broad live evaluations remain unmeasured; live synthetic browser acceptance now passes, as detailed in the latest entry. Production has no fake provider fallback.
- Retrieval Recall@10, generated claim support, appropriate abstention, provider latency, token usage: **not measured**, retained as null in evaluation output.
- Docker builds/Compose startup, CI execution, deployment, backup restore, production load and all race conditions: not verified here.

## Package choices

Frontend: Next.js 16.4.0, React/React DOM 19.3.0, TypeScript 5.9, Vitest 5.0.3, Playwright 1.63.0. Backend: Flask 3.1.3, SQLAlchemy 2.1.3, Celery 5.6.3, Psycopg 3.3.6, pgvector Python 0.5.0, Tree-sitter 0.25.2, google-genai 2.28.0. Exact transitive versions live in the committed lockfiles.

The implementation host used Node 24 and Python 3.14. The container targets Python 3.12. Cryptography 46.0.7 is constrained to the binary-compatible 46.x series because 50.x required an unavailable Rust build on this host. Pytest emitted deprecation warnings from Google SDK typing internals and Flask-Session's signer option; no test failure resulted.

## Model/API references

Documentation-informed defaults are `gemini-3.8-flash` for generation and `gemini-embedding-001` for text embeddings at 768 normalized dimensions. These are **not live-tested model choices**. The SDK adapter was imported and exercised with deterministic embedding doubles.

Official references consulted:
- [Google SDK libraries](https://ai.google.dev/gemini-api/docs/libraries)
- [Python SDK methods](https://googleapis.github.io/python-genai/)
- [Embeddings and retrieval task types](https://ai.google.dev/gemini-api/docs/embeddings)
- [Structured output/model documentation](https://ai.google.dev/gemini-api/docs/structured-output)
- [pgvector](https://github.com/pgvector/pgvector)

The embedding docs retain the text-only 001 model and document retrieval task types and reduced dimensions. The adapter uses `models.embed_content` and `models.generate_content` with Pydantic response validation. Check account access and run a live smoke test before release.

## Playback fix verification

The user reported stuttering. The original 1600×900 VP9 clip was replaced with a 960×540 H.264 MP4 (436 KB), and full-page grain animation was disabled. After reloading the actual in-app browser, the video reached readyState 4, its time advanced, and pause/resume toggled correctly. Screenshot: `screenshots/hero-video-optimized.png`. This verifies playback behavior, not a measured dropped-frame benchmark.


## User-requested 4K upgrade

The hero now uses an original native 3840×2160 H.264 MP4 (about 7 MB), rendered from canvas at full resolution. The in-app browser confirmed videoWidth 3840, videoHeight 2160, readyState 4, and active playback. A pearl-and-violet cursor light uses composited transforms, an easing loop that stops at rest, and is disabled for touch and reduced motion. The creator credit also appears below the home-page buttons in a purple gradient.

After this upgrade, all 12 public browser tests passed in Chrome, including six viewport layouts, 4K dimensions, pointer following, click-through behavior, and reduced-motion preferences.


## Private browser acceptance — 8 October 2026

Passed registration, authenticated dashboard, ZIP upload, sanitized source preview, consent, queued indexing through Redis/Celery, question submission, answer display, citation highlighting, guide generation, actual Markdown download and contents, reload, logout, login, and persisted project display. Browser reported no uncaught errors. The streaming test proxy intentionally returns 503 for SSE so the real polling fallback is exercised.

Only the external Gemini provider is substituted inside the test harness. No response fixtures replace the application API. Database tables are created/dropped only in the explicitly named test database, and test Redis databases are separate from the app. The production app never selects the test provider.

Reproduce from the repository root, with the frontend running on port 3000 and local services available:

```sh
backend/.venv/bin/python scripts/local_run.py --test .venv/bin/python -m tests.browser_flow
```

Do not run this concurrently with other tests using the same test database. Screenshot: `screenshots/private-flow-test.png`. Docker build context now excludes `.runtime` and private `.env.*` files.


## Live Gemini key smoke check — 8 October 2026

The user configured the root `.env` key. A real document embedding request succeeded with 768 dimensions; a plain generation request on gemini-3.8-flash also succeeded. The constrained Pydantic answer schema returned HTTP 400. The provider now sends an inlined structural schema without maxLength/maxItems, while retaining all local Answer validation limits. Requests with that schema returned HTTP 503 high-demand responses on gemini-3.8-flash and gemini-3.7-flash, including bounded retries. Full structured-answer generation remains unverified; do not represent the AI workflow as fully live-tested. No fallback model was configured. The API and worker were restarted to load the key. The regression suite passes 56 tests.


## Upload error and cursor scope — 8 October 2026

The user's upload reached Flask and received HTTP 413. The configured ZIP limit remains 25 MiB. Client validation now rejects oversized files before creating a project or submitting the file, reports its size, and suggests removing dependencies/build artifacts. Flask and non-JSON proxy 413 responses now have actionable messages. Next's proxy buffer limit is explicitly 26 MiB to accommodate the 25 MiB payload plus multipart overhead, matching nginx. The source-only ZIP limit itself was not increased without knowing the user's file size.

CursorLight is mounted only on Landing following the user's latest preference. It is absent from login, registration and workspace. Production build and 57 backend tests pass.


## Increased FYP upload capacity — 9 October 2026

ZIP limit raised from 25 to 100 MiB and expanded limit from 100 to 500 MiB in backend defaults and the local environment. Frontend validation/copy now match; Next.js and nginx allow 101 MiB for multipart overhead. A real 32 MiB ZIP passes the authenticated upload integration test, retaining supported source while excluding its large binary asset. All 58 backend tests and the frontend production build pass. API, worker, and frontend were restarted. Cursor remains exclusive to the home page.


## Archive entry capacity — 9 October 2026

Raised the total ZIP entry limit from 5,000 to 50,000 in defaults, sample configuration and the local environment. Limit errors now include the actual entry count, configured maximum and source-only ZIP guidance. A 5,002-entry fixture containing 5,001 dependency files passes; only main.py is included. Boundary rejection still passes. All 60 backend tests pass. The 100 MiB compressed, 500 MiB extracted and 2,000 indexed-source-file limits remain in force.


## Link-bearing repository ZIPs — 9 October 2026

Symlinks and special ZIP entries now produce exclusion-report rows instead of rejecting an otherwise valid repository. They never enter the member-reading or .gitignore-reading passes. Parameterized tests cover symlinks, FIFOs, sockets, character and block devices, prove excluded members are not opened, and retain rejection for archives with no supported source. All 65 backend tests pass. This refines the original whole-archive rejection behavior while continuing to exclude link/special content.


## Live acceptance and error recovery — 9 October 2026

This supersedes the earlier live-AI blockers. Real Gemini browser acceptance passed using gemini-3.5-flash: synthetic ZIP upload, real 768-dimensional embedding/indexing, query embedding, cited answer, support review, citation navigation, onboarding guide, actual Markdown download, reload, logout/login and persisted project. No private repository content was sent; the fixture is only `def hello(): return 42`. The application and worker now use the verified model. gemini-3.8-flash continued to return 503; no fake fallback is used by the application.

Opt in (billable API calls, isolated test database; do not run with another test-database suite):

```sh
CODEBUDDY_LIVE_TEST=1 backend/.venv/bin/python scripts/local_run.py --test .venv/bin/python -m tests.browser_flow
```

Additional fixes: provider errors explain outage/quota/access failures without exposing payloads; corrupt ZIP members return actionable validation errors; exclusion reports render 100 rows per page; source preview, discard and sign-out failures are caught; successful job updates clear stale errors; malformed SSE events fall back to polling. Regression tests cover these error paths. Production build, 71 backend tests and 7 frontend tests passed. The user has one project but no successfully uploaded source snapshot as of the pre-test inspection. Hosting remains unprovisioned.

Final browser verification after recovery fixes: all 12 public Chrome tests passed, and the complete isolated private flow passed with no uncaught page errors. Includes home-only cursor scope and oversized-file feedback.


## Nested archive handling — 9 October 2026

Nested ZIP/TAR/GZ/7z entries are skipped and reported rather than rejecting the whole repository. Regression tests guard member reads to prove nested archive contents are never opened, confirm ordinary source remains available, and preserve a clear no-supported-source error for archives containing only another archive.

## Long source lines — 12 October 2026

The first real repository ingestion failed during chunking because three CSS files contained lines longer than the 12,000-character chunk limit. New uploads now exclude such files with an explicit report reason. Existing saved previews remain retryable: the worker preserves the source files, marks them excluded from indexing, and processes the remaining files. An entirely excluded snapshot fails clearly instead of becoming an empty active snapshot. All 76 backend tests passed, including new real-database regression cases for existing previews with mixed source and with only oversized lines.

The actual saved repository was retried with its existing processing consent. Chunking completed with 400 chunks; embedding reached 112 chunks before Gemini returned a quota/rate-limit failure. The job now exposes the specific provider-limit message. Real-repository ingestion has therefore not completed successfully; provider quota must be available before retrying.

## Rate-limit recovery — 12 October 2026

A later single synthetic embedding request succeeded. Added ten-second pacing between embedding batches and bounded backoff honoring Gemini RetryInfo (60-second fallback for 429). Completed embeddings are reused by content hash within the same snapshot only when the recorded model and dimension match. New regression cases verify retry completion without duplicate embedding calls and invalidation on a model change. All 82 backend tests passed. A user-triggered retry before this fix had already discarded the previous partial embeddings; a single additional recovery retry was queued after the fix without resetting attempt history.

Recovery succeeded on the actual uploaded repository: the job completed with stage `ready` and progress `400 / 400`. The original three oversized-line CSS files remained explicitly excluded from indexing. This verifies real-repository indexing; real-repository answer quality is still a separate acceptance check.
