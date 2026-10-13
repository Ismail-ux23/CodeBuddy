# Contributing to CodeBuddy

Small, focused bug fixes, tests, accessibility improvements, and documentation updates are welcome.
For a larger feature, open an issue explaining the problem and proposed behavior first.

## Development

Follow [setup](docs/setup.md). Install the locked dependencies with `make install`.
Create a branch from `main`, make one focused change, and run:

```sh
make lint
make test
make build
python3 scripts/verify_demo.py
cd frontend && npx playwright install chromium && npm run test:e2e
```

For database/session/worker changes, run the integration suite against disposable PostgreSQL
with pgvector and Redis. Fixtures delete tables; never point tests at application data.
See [setup](docs/setup.md#integration-tests) for the test variables.

Add regression coverage for behavior changes. State which checks ran and any skipped checks
in the pull request. Keep demo fixtures synthetic. Never submit API keys, user source, passwords,
local databases, dependencies, or build outputs. Report vulnerabilities privately via [SECURITY.md](SECURITY.md).

Use concise commit messages that describe the behavior changed. Pull requests should explain
the problem, the resulting behavior, and validation. Contributions are licensed under [MIT](LICENSE).
