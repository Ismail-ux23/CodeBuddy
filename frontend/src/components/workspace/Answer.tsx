"use client";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
export default function Answer({
  answer,
  onCitation,
}: {
  answer: any;
  onCitation: (c: any) => void;
}) {
  return (
    <div className="answer">
      {answer.label && <span className="demo-label">{answer.label}</span>}
      {answer.answer_status === "insufficient_evidence" && (
        <p className="notice">Insufficient evidence in this snapshot.</p>
      )}
      {answer.claims?.map((claim: any, i: number) => (
        <div className="claim" key={i}>
          <span className={`evidence-label ${claim.evidence_kind}`}>
            {claim.evidence_kind === "observed"
              ? "Supported by source"
              : claim.evidence_kind === "inferred"
                ? "Inference"
                : "General explanation"}
          </span>
          <ReactMarkdown
            skipHtml
            rehypePlugins={[rehypeSanitize]}
            components={{
              a: ({ children }) => <span>{children}</span>,
              img: () => null,
            }}
          >
            {claim.text}
          </ReactMarkdown>
          <div className="citations">
            {claim.source_ids.map((id: string) => {
              const c = answer.citations?.find((c: any) => c.source_id === id);
              return c ? (
                <button
                  key={id}
                  onClick={() => onCitation(c)}
                  title={`Open ${c.path} lines ${c.start_line}–${c.end_line}`}
                >
                  <span>↗</span> {c.path.split("/").pop()}:{c.start_line}–
                  {c.end_line}
                </button>
              ) : null;
            })}
          </div>
        </div>
      ))}
      {answer.limitations?.length > 0 && (
        <details className="limitations">
          <summary>Limitations</summary>
          <ul>
            {answer.limitations.map((s: string, i: number) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </details>
      )}
      {answer.follow_up_questions?.map((s: string) => (
        <p className="muted small" key={s}>
          {s}
        </p>
      ))}
    </div>
  );
}
