"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import Icon from "@/components/shared/Icon";
export default function Dashboard() {
  const [filter, setFilter] = useState("");
  const q = useQuery({
    queryKey: ["projects"],
    queryFn: () => api("/projects"),
  });
  return (
    <main className="dashboard">
      <div className="section-head">
        <div>
          <p className="eyebrow">WORKSPACE</p>
          <h1>Your projects</h1>
          <p className="muted">A little context goes a long way.</p>
        </div>
        <Link className="button solid" href="/app/new">
          <Icon name="plus" />
          New project
        </Link>
      </div>
      <label className="search-field">
        <Icon name="search" />
        <input
          aria-label="Search projects"
          placeholder="Find a project…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </label>
      {q.isPending ? (
        <p className="muted">Loading projects…</p>
      ) : q.error ? (
        <p role="alert" className="error">
          {q.error.message}
        </p>
      ) : q.data.items.length === 0 ? (
        <div className="empty-state">
          <Icon name="folder" />
          <h2>Your next discovery starts here.</h2>
          <p>
            Upload a repository ZIP to explore its files, ask questions, and
            build an onboarding guide.
          </p>
          <Link href="/app/new" className="button solid">
            Analyze your first repository
          </Link>
          <Link href="/demo" className="text-link">
            Take a look at the demo →
          </Link>
        </div>
      ) : (
        <div className="project-grid">
          {q.data.items
            .filter((p: any) =>
              p.name.toLowerCase().includes(filter.toLowerCase()),
            )
            .map((p: any) => (
              <Link
                className="project-card"
                key={p.id}
                href={`/app/projects/${p.id}`}
              >
                <div className="row">
                  <Icon name="folder" />
                  <span
                    className={`status ${p.active_snapshot_id ? "ready" : ""}`}
                  >
                    {p.active_snapshot_id ? "Indexed" : "Awaiting source"}
                  </span>
                </div>
                <h2>{p.name}</h2>
                <p>
                  {p.description || "Explore the source behind this project."}
                </p>
                <p className="small">
                  {p.file_count} files ·{" "}
                  {p.languages?.join(" / ") || "No indexed languages"}
                </p>
                <div className="card-bottom">
                  <span>
                    Updated {new Date(p.updated_at).toLocaleDateString()}
                  </span>
                  <Icon name="arrow" />
                </div>
              </Link>
            ))}
        </div>
      )}
    </main>
  );
}
