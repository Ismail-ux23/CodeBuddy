# Security policy

CodeBuddy is a portfolio project under active development, not a production security certification.
Only the latest `main` revision is maintained.

## Reporting a vulnerability

Email **ismailmanzoor1903@gmail.com** with a description, affected revision, reproduction steps,
and expected impact. Please do not post credentials, private source code, or exploitable details
in a public issue. No response-time or security-support SLA is offered.

## Deployment boundaries

- Set a random `APP_SECRET_KEY`, production cookie settings, HTTPS, and a strong database password.
- Keep Gemini keys server-side; never use `NEXT_PUBLIC_*` for credentials.
- Source uploaded to CodeBuddy may be sent to Gemini only after indexing consent.
- Automated redaction is heuristic. Inspect the source preview and exclude confidential files yourself.
- Uploaded code is read as text, never executed and its dependencies are never installed.
- Use disposable test databases; integration fixtures drop tables.

See [security and data flow](docs/security-and-data-flow.md) and [limitations](docs/limitations.md).
