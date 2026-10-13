from app.schemas import Answer


def validate_answer(answer: Answer, evidence: dict):
    result = answer.model_dump()
    citations = {}
    valid = []
    dropped = False
    for claim in result["claims"]:
        ids = claim["source_ids"]
        if any(i not in evidence for i in ids) or (claim["evidence_kind"] != "general" and not ids):
            dropped = True
            continue
        for i in ids:
            e = evidence[i]
            if not (1 <= e["start_line"] <= e["end_line"] <= e["line_count"]):
                raise ValueError("Invalid server evidence range")
            citations[i] = {k: e[k] for k in ("source_id", "file_id", "snapshot_id", "path", "start_line", "end_line")}
        valid.append(claim)
    result["claims"] = valid
    result["citations"] = list(citations.values())
    if dropped:
        result["answer_status"] = "partial" if valid else "insufficient_evidence"
        result["limitations"].append("Claims with missing or invalid evidence were removed.")
    if not valid:
        result["answer_status"] = "insufficient_evidence"
    return result
