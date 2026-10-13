"""Fixture validation by default; real hybrid retrieval measurement when explicitly configured."""
import argparse
import json
import os
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--retrieval", action="store_true")
parser.add_argument("--snapshot")
parser.add_argument("--owner")
args = parser.parse_args()
cases = [json.loads(line) for line in (root / "evals/cases.jsonl").read_text().splitlines()]
for c in cases:
    for e in c["evidence"]:
        lines = (root / "demo/repository" / e["path"]).read_text().splitlines()
        assert 1 <= e["start_line"] <= e["end_line"] <= len(lines), c["id"]
result = dict(cases=len(cases),abstention_cases=sum(c["expected_status"]=="insufficient_evidence" for c in cases), labeled_ranges_valid=True,
    retrieval_recall_at_10=None,claim_support=None,abstention_accuracy=None,latency_seconds=None,token_usage=None)
if args.retrieval:
    if not args.snapshot or not args.owner: parser.error("--retrieval requires --snapshot and --owner")
    sys.path.insert(0,str(root / "backend"))
    from app import create_app
    from app.extensions import db
    from app.models import Snapshot, Project
    from app.providers.gemini import Gemini
    from app.rag.retrieval import retrieve
    with create_app().app_context():
        snapshot = db.session.get(Snapshot,args.snapshot)
        project = db.session.get(Project,snapshot.project_id) if snapshot else None
        if not project or project.owner_id != args.owner or project.deleting or snapshot.status != "ready":
            raise ValueError("Ready snapshot owned by the supplied owner required")
        provider = Gemini(); hits=0; total=0
        for c in cases:
            if not c["evidence"]: continue
            evidence = list(retrieve(snapshot,c["question"],provider).values())
            for label in c["evidence"]:
                total+=1
                hits+=any(e["path"]==label["path"] and e["start_line"]<=label["end_line"] and e["end_line"]>=label["start_line"] for e in evidence)
        result["retrieval_recall_at_10"] = hits/total if total else None
        result["retrieval_labeled_ranges"] = total
print(json.dumps(result,indent=2))
