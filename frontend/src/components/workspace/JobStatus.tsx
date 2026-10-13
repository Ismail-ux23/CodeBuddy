"use client";
import { useEffect, useRef, useState } from "react";
import { api, post } from "@/lib/api";
export default function JobStatus({
  id,
  onDone,
}: {
  id: string;
  onDone: () => void;
}) {
  const [job, setJob] = useState<any>(null),
    [error, setError] = useState("");
  const done = useRef(onDone);
  done.current = onDone;
  useEffect(() => {
    setJob(null);
    setError("");
    let active = true,
      finished = false;
    const update = (j: any) => {
      if (!active) return;
      setJob(j);
      setError("");
      if (j.status === "completed" && !finished) {
        finished = true;
        done.current();
      }
    };
    const poll = () =>
      api(`/jobs/${id}`)
        .then(update)
        .catch((e) => active && setError(e.message));
    poll();
    const timer = setInterval(poll, 3000);
    const source = new EventSource(`/api/v1/jobs/${id}/events`);
    source.addEventListener("status", (e) => {
      try { update(JSON.parse((e as MessageEvent).data)); }
      catch { source.close(); } // Polling continues if an event is malformed.
    });
    source.onerror = () => source.close();
    return () => {
      active = false;
      clearInterval(timer);
      source.close();
    };
  }, [id]);
  const terminal =
    job && ["completed", "failed", "cancelled"].includes(job.status);
  return (
    <div className="job-status" aria-live="polite">
      <div className="row spread">
        <strong>{job?.stage || "Queued"}</strong>
        {job?.total > 0 && (
          <span>
            {job.completed} / {job.total}
          </span>
        )}
      </div>
      {!terminal && (
        <>
          <div className="indeterminate" />
          <p className="muted small">
            Processing in the background. Closing this page does not cancel the
            job.
          </p>
          <button
            className="button ghost"
            onClick={() =>
              post(`/jobs/${id}/cancel`)
                .then(setJob)
                .catch((e) => setError(e.message))
            }
          >
            Cancel
          </button>
          <p className="muted small">
            Provider requests already sent may still incur charges.
          </p>
        </>
      )}
      {job?.error_message && <p className="error">{job.error_message}</p>}
      {["failed", "cancelled"].includes(job?.status) && (
        <button
          className="button ghost"
          onClick={() =>
            post(`/jobs/${id}/retry`)
              .then(setJob)
              .catch((e) => setError(e.message))
          }
        >
          Retry job
        </button>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
