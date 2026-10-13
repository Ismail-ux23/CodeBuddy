"use client";
import { useState } from "react";
import { api, post, allPages } from "@/lib/api";
import JobStatus from "./JobStatus";
export default function Upload({ projectId }: { projectId?: string }) {
  const [name, setName] = useState(""),
    [description, setDescription] = useState(""),
    [file, setFile] = useState<File | null>(null),
    [patterns, setPatterns] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [snapshot, setSnapshot] = useState<any>(null),
    [pid, setPid] = useState(projectId || ""),
    [files, setFiles] = useState<any[]>([]),
    [excluded, setExcluded] = useState<string[]>([]),
    [job, setJob] = useState(""),
    [consent, setConsent] = useState(false),
    [preview, setPreview] = useState<any>(null),
    [reportPage, setReportPage] = useState(0);
  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    if (file.size > 100 * 1024 * 1024) {
      setError(`Your ZIP is ${(file.size / 1024 / 1024).toFixed(1)} MiB. The upload limit is 100 MiB. Create a source-only ZIP without node_modules, .git, .venv, build outputs, or videos, then try again.`);
      return;
    }
    setBusy(true);
    setError("");
    try {
      let id = pid;
      if (!id) {
        id = (await post("/projects", { name, description })).id;
        setPid(id);
      }
      const data = new FormData();
      data.append("file", file);
      data.append("exclusions", patterns);
      const s = await api(`/projects/${id}/uploads`, {
        method: "POST",
        body: data,
      });
      setSnapshot(s);
      setReportPage(0);
      setFiles(await allPages(`/projects/${id}/files?snapshot_id=${s.id}`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function index() {
    setBusy(true);
    setError("");
    try {
      const j = await post(
        `/uploads/${snapshot.id}/index`,
        { consent, exclude_file_ids: excluded },
        crypto.randomUUID(),
      );
      setJob(j.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="upload-flow">
      {!snapshot ? (
        <form onSubmit={upload}>
          {!projectId && (
            <>
              <label>
                Project name
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  maxLength={100}
                  placeholder="e.g. My application"
                />
              </label>
              <label>
                Description <span className="muted">(optional)</span>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  maxLength={2000}
                  rows={2}
                />
              </label>
            </>
          )}
          <label
            className="dropzone"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              setFile(e.dataTransfer.files[0]);
            }}
          >
            <span className="upload-symbol">↑</span>
            <strong>
              {file ? file.name : "Drop your repository ZIP here"}
            </strong>
            <span>or choose a file · up to 100 MiB</span>
            <input
              aria-label="Repository ZIP"
              type="file"
              accept=".zip,application/zip"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required={!file}
            />
          </label>
          <label>
            Exclude patterns <span className="muted">(one per line)</span>
            <textarea
              value={patterns}
              onChange={(e) => setPatterns(e.target.value)}
              placeholder={"private/**\nexperiments/**"}
              rows={3}
            />
          </label>
          <div className="info-box">
            <strong>You stay in control.</strong>
            <p>
              CodeBuddy reads your source; it never runs repository code or
              installs its dependencies. Review sanitized files before approving
              external AI processing. Secret detection is best-effort.
            </p>
          </div>
          <button className="button solid" disabled={busy || !file}>
            {busy ? "Uploading and validating…" : "Upload & preview"}
          </button>
        </form>
      ) : (
        <>
          <div className="row spread">
            <h2>Review your source</h2>
            <span className="status">{snapshot.file_count} files</span>
          </div>
          <p className="muted">
            Uncheck files to exclude them from indexing. Select a path to
            inspect the sanitized source.
          </p>
          <div className="preview-list">
            {files.map((f) => (
              <div className="row" key={f.id}>
                <input
                  aria-label={`Include ${f.relative_path}`}
                  type="checkbox"
                  checked={!excluded.includes(f.id)}
                  onChange={(e) =>
                    setExcluded(
                      e.target.checked
                        ? excluded.filter((id) => id !== f.id)
                        : [...excluded, f.id],
                    )
                  }
                />
                <button
                  className="file-link"
                  onClick={async () => {
                    try {
                      setError("");
                      setPreview(await api(`/projects/${pid}/files/${f.id}?snapshot_id=${snapshot.id}`));
                    } catch (e) { setError((e as Error).message); }
                  }}
                >
                  {f.relative_path}
                </button>
                <span className="muted">{f.line_count} lines</span>
              </div>
            ))}
          </div>
          {preview && (
            <details open>
              <summary>{preview.relative_path} · sanitized preview</summary>
              <pre className="source-preview">{preview.text}</pre>
            </details>
          )}
          <details>
            <summary>
              Exclusion & redaction report ({snapshot.report.length})
            </summary>
            <ul className="report-list">
              {snapshot.report.slice(reportPage * 100, (reportPage + 1) * 100).map((f: any) => (
                <li key={f.path}>
                  <code>{f.path}</code>
                  <span>{f.reason}</span>
                </li>
              ))}
            </ul>
            {snapshot.report.length > 100 && <div className="row">
              <button className="button ghost" disabled={reportPage === 0} onClick={() => setReportPage(p => p - 1)}>Previous entries</button>
              <span>Page {reportPage + 1} of {Math.ceil(snapshot.report.length / 100)}</span>
              <button className="button ghost" disabled={(reportPage + 1) * 100 >= snapshot.report.length} onClick={() => setReportPage(p => p + 1)}>Next entries</button>
            </div>}
          </details>
          {!job && (
            <>
              <label className="check-label">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                />
                I understand that supported sanitized source excerpts are sent
                to Google Gemini for embeddings and answers.
              </label>
              <div className="row">
                <button
                  className="button solid"
                  disabled={
                    !consent || busy || excluded.length === files.length
                  }
                  onClick={index}
                >
                  Start indexing
                </button>
                <button
                  className="button ghost"
                  onClick={async () => {
                    try {
                      await api(`/uploads/${snapshot.id}`, { method: "DELETE" });
                      setSnapshot(null); setPreview(null); setExcluded([]); setError("");
                    } catch (e) { setError((e as Error).message); }
                  }}
                >
                  Discard upload
                </button>
              </div>
            </>
          )}
          {job && (
            <JobStatus
              id={job}
              onDone={() => location.assign(`/app/projects/${pid}`)}
            />
          )}
        </>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </div>
  );
}
