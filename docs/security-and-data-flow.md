# Security and data flow

API ownership is checked through project → snapshot → file/conversation/job/guide relationships. UUID secrecy is not an access control. Unknown and foreign private records return 404. All source paths are labels; reads use stored UUID keys under a private root. Snapshot IDs from citation clicks remain pinned, even after new uploads.

Argon2 hashes protect passwords. Authentication rotates Redis sessions. Cookies are HttpOnly, SameSite=Lax, and Secure in production, with a 12-hour lifetime. Logout removes the current session; account deletion makes every remaining session fail user loading. CSRF is required for state-changing JSON and multipart requests. Redis backs request rate limits. Browser source is rendered as text by CodeMirror. Markdown HTML and images are disabled; model links render as text to prevent surprise navigation.

No private source or model prompt is logged by application code. Errors expose safe messages and request IDs. Job usage stores provider/model, versions, latency, and returned token metadata. Google receives source chunks for embeddings and selected excerpts for answers after consent. Provider-side retention is governed by the configured account’s Google terms; this app cannot erase provider logs.

Original ZIP bytes exist only during validation and are never saved. Sanitized snapshots persist until project/account deletion. Unconfirmed previews expire after 24 hours when beat/cleanup runs. Usage/audit metadata expire after 30 days. Redis sessions expire automatically. Deployment backups are operator-managed; deleting live data does not erase external backups. Document actual backup retention before onboarding real users.

The scanner handles common credential assignments, common token formats, secret filenames, and private-key blocks, but has false positives and false negatives. `.gitignore` support is conservative for root-level files; arbitrary nested Git semantics are not guaranteed. Code text, README instructions, and comments are untrusted; they never trigger shell execution or network fetching.

Nginx is the intended single entry point. The current CSP allows inline Next.js bootstrap scripts; adopt per-request CSP nonces for a stricter production policy. Do not expose Flask directly behind arbitrary forwarded headers. Only enable trusted proxy handling when a known proxy overwrites those headers. Production HTTPS is required for secure cookies. Email verification/reset and GitHub tokens are intentionally absent.
