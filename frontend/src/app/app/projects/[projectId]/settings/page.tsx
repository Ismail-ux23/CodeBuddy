"use client";
import { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import Upload from "@/components/workspace/Upload";
export default function Settings({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const q = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api(`/projects/${projectId}`),
  });
  const [name, setName] = useState(""),
    [error, setError] = useState("");
  return (
    <main className="narrow-page">
      <p className="eyebrow">PROJECT</p>
      <h1>{q.data?.name || "Settings"}</h1>
      {q.error && <p className="error">{q.error.message}</p>}
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await api(`/projects/${projectId}`, {
              method: "PATCH",
              body: JSON.stringify({
                name,
                description: q.data?.description || "",
              }),
            });
            q.refetch();
          } catch (e) {
            setError((e as Error).message);
          }
        }}
      >
        <label>
          Rename project
          <input
            required
            maxLength={100}
            placeholder={q.data?.name}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <button className="button ghost">Save name</button>
      </form>
      <h2 className="section-title">Snapshot history</h2>
      <div className="snapshot-list">
        {q.data?.snapshots?.map((s: any) => (
          <a key={s.id} href={`/app/projects/${projectId}?snapshot=${s.id}`}>
            {new Date(s.created_at).toLocaleString()} · {s.status} ·{" "}
            {s.file_count} files <code>{s.id.slice(0, 8)}</code>
          </a>
        ))}
      </div>
      <h2 className="section-title">Upload a new snapshot</h2>
      <p className="muted">
        Existing conversations and citations stay pinned to their original
        source.
      </p>
      <Upload projectId={projectId} />
      <p className="error" role="alert">
        {error}
      </p>
      <div className="danger-zone">
        <h2>Delete project</h2>
        <p>Deletes private source and derived data. This cannot be undone.</p>
        <button
          className="button ghost danger"
          onClick={async () => {
            if (!confirm("Delete this project and all its snapshots?")) return;
            try {
              await api(`/projects/${projectId}`, { method: "DELETE" });
              location.assign("/app");
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          Delete project
        </button>
      </div>
    </main>
  );
}
