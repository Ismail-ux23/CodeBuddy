# Evaluation

`python3 evals/run.py` validates 24 hand-authored cases against the bundled source snapshot, including six abstentions and three partial responses. The expected behaviors were checked against the fixture source during implementation. This validates labels and ranges, **not model quality**.

After uploading and genuinely indexing `demo/quiz-garden.zip`, run from the project root with backend dependencies and server configuration:

```sh
backend/.venv/bin/python evals/run.py --retrieval --snapshot SNAPSHOT_UUID --owner USER_UUID
```

This makes billable query-embedding calls and measures evidence-range Recall@10 using actual PostgreSQL/pgvector retrieval. It checks ownership before querying. It does not substitute keyword search for semantic retrieval.

For each generated answer, manually record claim support (supported claims / repository-specific claims), citation validity, and appropriate abstention against `manual_expectation`. Record latency and provider usage from the persisted job. Do not call a citation faithful merely because its path exists. The model support pass is a heuristic. Missing metrics remain null. The tiny original fixture is not representative of large enterprise repositories.
