"use client";
import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, post, allPages } from "@/lib/api";
import demoData from "@/lib/demo.json";
import Brand from "@/components/shared/Brand";
import Icon from "@/components/shared/Icon";
import Answer from "./Answer";
import JobStatus from "./JobStatus";
const CodeViewer = dynamic(() => import("./CodeViewer"), {
  ssr: false,
  loading: () => <p className="loading">Opening source…</p>,
});
export default function Workspace({
  projectId,
  demo = false,
}: {
  projectId?: string;
  demo?: boolean;
}) {
  const cache = useQueryClient();
  const [snapshot, setSnapshot] = useState(""),
    [fid, setFid] = useState(""),
    [range, setRange] = useState<[number, number] | null>(null),
    [filter, setFilter] = useState(""),
    [tab, setTab] = useState("code"),
    [panel, setPanel] = useState("chat"),
    [question, setQuestion] = useState(""),
    [conversation, setConversation] = useState(""),
    [job, setJob] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [demoAnswer, setDemoAnswer] = useState<any>(null),
    [selection, setSelection] = useState<[number, number] | null>(null),
    [width, setWidth] = useState(400),
    [search, setSearch] = useState(""),
    [results, setResults] = useState<any[]>([]),
    [feedback, setFeedback] = useState(""),
    [opened, setOpened] = useState<string[]>([]);
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api("/auth/me"),
    enabled: !demo,
  });
  useEffect(() => {
    if (me.data?.user?.id) {
      try {
        const stored = Number(
          localStorage.getItem(`codebuddy-layout:${me.data.user.id}`),
        );
        if (stored >= 320 && stored <= 560) setWidth(stored);
      } catch {}
    }
  }, [me.data?.user?.id]);
  useEffect(() => {
    if (me.data?.user?.id) {
      try {
        localStorage.setItem(
          `codebuddy-layout:${me.data.user.id}`,
          String(width),
        );
      } catch {}
    }
  }, [width, me.data?.user?.id]);
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api(`/projects/${projectId}`),
    enabled: !demo,
  });
  const active =
    snapshot ||
    project.data?.active_snapshot_id ||
    project.data?.snapshots?.[0]?.id ||
    "";
  const sid = demo ? demoData.manifest.snapshot_id : active;
  const fileQuery = useQuery({
    queryKey: ["files", projectId, sid],
    queryFn: () => allPages(`/projects/${projectId}/files?snapshot_id=${sid}`),
    enabled: !demo && !!sid,
  });
  const files: any[] = demo ? demoData.files : fileQuery.data || [];
  const selected = files.find((f) => f.id === fid) || files[0];
  const source = useQuery({
    queryKey: ["source", projectId, sid, selected?.id],
    queryFn: () =>
      api(`/projects/${projectId}/files/${selected.id}?snapshot_id=${sid}`),
    enabled: !demo && !!selected,
  });
  const content = demo ? selected : source.data;
  const conversations = useQuery({
    queryKey: ["conversations", projectId],
    queryFn: () => api(`/projects/${projectId}/conversations`),
    enabled: !demo,
  });
  const conversationState = useQuery({
    queryKey: ["conversation-state", conversation],
    queryFn: () => api(`/conversations/${conversation}`),
    enabled: !demo && !!conversation,
  });
  useEffect(() => {
    const pending = conversationState.data?.jobs?.find((j: any) =>
      ["queued", "running"].includes(j.status),
    );
    if (pending) setJob(pending.id);
  }, [conversationState.data]);
  const messages = useQuery({
    queryKey: ["messages", conversation],
    queryFn: () => allPages(`/conversations/${conversation}/messages`),
    enabled: !demo && !!conversation,
  });
  const guides = useQuery({
    queryKey: ["guides", projectId, sid],
    queryFn: () => api(`/projects/${projectId}/guides?snapshot_id=${sid}`),
    enabled:
      !demo &&
      !!sid &&
      project.data?.snapshots?.some(
        (s: any) => s.id === sid && s.status === "ready",
      ),
  });
  useEffect(() => {
    if (!demo) {
      const from = new URLSearchParams(location.search).get("snapshot");
      if (from) setSnapshot(from);
    }
  }, [demo]);
  const onSelection = useCallback(
    (a: number, b: number) => setSelection([a, b]),
    [],
  );
  useEffect(() => {
    if (selected?.id)
      setOpened((t) =>
        t.includes(selected.id) ? t : [...t.slice(-7), selected.id],
      );
  }, [selected?.id]);
  function cite(c: any) {
    setSelection(null);
    setSnapshot(c.snapshot_id);
    setFid(c.file_id);
    setRange([c.start_line, c.end_line]);
    setTab("code");
  }
  function finished() {
    setJob("");
    cache.invalidateQueries({ queryKey: ["project", projectId] });
    cache.invalidateQueries({ queryKey: ["messages", conversation] });
    cache.invalidateQueries({ queryKey: ["guides", projectId] });
    cache.invalidateQueries({ queryKey: ["conversations", projectId] });
  }
  async function send() {
    if (!question.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      let id = conversation;
      if (!id) {
        id = (
          await post(`/projects/${projectId}/conversations`, {
            snapshot_id: sid,
          })
        ).id;
        setConversation(id);
      }
      const data: any = { question };
      if (selection && selected) {
        data.file_id = selected.id;
        data.start_line = selection[0];
        data.end_line = selection[1];
      }
      const j = await post(
        `/conversations/${id}/messages`,
        data,
        crypto.randomUUID(),
      );
      setJob(j.id);
      setQuestion("");
      cache.invalidateQueries({ queryKey: ["messages", id] });
      setSelection(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const guide = demo
    ? demoData.answers.find((a) => a.id === "onboarding")
    : guides.data?.items?.[0]?.content;
  return (
    <div
      className={`workspace ${demo ? "demo-workspace" : ""}`}
      style={{ "--chat-width": `${width}px` } as React.CSSProperties}
    >
      <header className="workspace-top">
        {demo ? (
          <Brand />
        ) : (
          <Link href="/app" className="muted">
            ← Projects
          </Link>
        )}
        <span className="workspace-name">
          {demo ? "Quiz Garden" : project.data?.name || "Project"}
        </span>
        <span className="snapshot-badge">
          {demo ? "Bundled demo" : `Snapshot ${sid.slice(0, 8) || "pending"}`}
        </span>
        <div className="top-actions">
          {demo ? (
            <Link href="/register" className="button solid">
              Analyze your code
            </Link>
          ) : (
            <Link
              href={`/app/projects/${projectId}/settings`}
              aria-label="Project settings"
            >
              <Icon name="settings" />
            </Link>
          )}
        </div>
      </header>
      {demo && (
        <div className="demo-banner">
          READ-ONLY DEMO{" "}
          <span>
            An original Flask quiz app. Answers are precomputed against this
            exact source.
          </span>
        </div>
      )}
      <nav className="mobile-tabs" aria-label="Workspace panels">
        {["files", "code", "chat", "guide"].map((t) => (
          <button
            key={t}
            className={tab === t ? "active" : ""}
            onClick={() => {
              setTab(t);
              if (t === "chat" || t === "guide") setPanel(t);
            }}
          >
            {t}
          </button>
        ))}
      </nav>
      <div className="workspace-body">
        <aside
          className={`file-pane ${tab === "files" ? "mobile-visible" : ""}`}
        >
          <div className="pane-title">
            EXPLORER <span>{files.length}</span>
          </div>
          <label className="file-filter">
            <Icon name="search" />
            <input
              aria-label="Find file"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Find a file…"
            />
          </label>
          <div className="file-tree">
            {Array.from(
              new Set(
                files.map((f) =>
                  f.relative_path.includes("/")
                    ? f.relative_path.split("/").slice(0, -1).join("/")
                    : "",
                ),
              ),
            )
              .sort()
              .map((dir) => (
                <details key={dir} open>
                  <summary>
                    <Icon name="folder" />
                    {dir || "/"}
                  </summary>
                  {files
                    .filter(
                      (f) =>
                        (f.relative_path.includes("/")
                          ? f.relative_path.split("/").slice(0, -1).join("/")
                          : "") === dir &&
                        f.relative_path
                          .toLowerCase()
                          .includes(filter.toLowerCase()),
                    )
                    .map((f) => (
                      <button
                        key={f.id}
                        className={`file-item ${selected?.id === f.id ? "selected" : ""}`}
                        onClick={() => {
                          setFid(f.id);
                          setRange(null);
                          setSelection(null);
                          setTab("code");
                        }}
                      >
                        <span className={`file-type ${f.language}`}>
                          {f.language === "py"
                            ? "py"
                            : f.language === "md"
                              ? "M↓"
                              : "{}"}
                        </span>
                        <span>{f.relative_path.split("/").pop()}</span>
                      </button>
                    ))}
                </details>
              ))}
          </div>
          {!demo && (
            <div className="history">
              <div className="pane-title">
                CONVERSATIONS{" "}
                <button
                  aria-label="New conversation"
                  onClick={() => {
                    setConversation("");
                    setJob("");
                    setSnapshot(project.data?.active_snapshot_id || "");
                  }}
                >
                  +
                </button>
              </div>
              {conversations.data?.items?.map((c: any) => (
                <button
                  key={c.id}
                  className={conversation === c.id ? "selected" : ""}
                  onClick={() => {
                    setConversation(c.id);
                    setSnapshot(c.snapshot_id);
                    setFid("");
                    setRange(null);
                    setSelection(null);
                    setPanel("chat");
                    setTab("chat");
                  }}
                >
                  <Icon name="chat" />
                  {c.title}
                </button>
              ))}
              {conversation && (
                <button
                  className="muted small"
                  onClick={async () => {
                    if (!confirm("Delete this conversation?")) return;
                    try {
                      await api(`/conversations/${conversation}`, {
                        method: "DELETE",
                      });
                      setConversation("");
                      cache.invalidateQueries({
                        queryKey: ["conversations", projectId],
                      });
                    } catch (e) {
                      setError((e as Error).message);
                    }
                  }}
                >
                  Delete conversation
                </button>
              )}
            </div>
          )}
          <div className="explorer-bottom">
            <span>Read-only source</span>
            <span className="creator-credit">Powered by Malik Ismail Manzoor</span>
          </div>
        </aside>
        <section
          className={`code-pane ${tab === "code" ? "mobile-visible" : ""}`}
        >
          <div
            className="source-tabs"
            role="tablist"
            aria-label="Open source files"
          >
            {opened.map((id) => {
              const f = files.find((f) => f.id === id);
              return f ? (
                <button
                  key={id}
                  role="tab"
                  aria-selected={selected?.id === id}
                  onClick={() => {
                    setFid(id);
                    setRange(null);
                    setSelection(null);
                  }}
                >
                  {f.relative_path.split("/").pop()}
                </button>
              ) : null;
            })}
          </div>
          <div className="code-toolbar">
            <span>
              <Icon />
              {selected?.relative_path || "Source"}
            </span>
            <span className="muted small">
              {content?.line_count || 0} lines
            </span>
          </div>
          {range && (
            <div className="citation-bar">
              Citation · lines {range[0]}–{range[1]} · snapshot{" "}
              {sid.slice(0, 8)}
              <button onClick={() => setRange(null)}>Clear</button>
            </div>
          )}
          {content ? (
            <CodeViewer
              key={`${sid}:${selected?.id}`}
              text={content.text}
              language={content.language}
              start={range?.[0]}
              end={range?.[1]}
              onSelection={onSelection}
            />
          ) : (
            <div className="empty-state">
              <Icon />
              <h2>
                {source.error
                  ? "Unable to open source"
                  : "Your source belongs here."}
              </h2>
              <p>
                {source.error?.message ||
                  "Upload a repository to start browsing its files."}
              </p>
              {!demo && (
                <Link
                  className="button ghost"
                  href={`/app/projects/${projectId}/settings`}
                >
                  Upload source
                </Link>
              )}
            </div>
          )}
          <div className="code-status">
            <span>{selected?.language || "text"} · UTF-8 · Read only</span>
            {selection && (
              <button
                onClick={() => {
                  setQuestion(
                    `Explain lines ${selection[0]}–${selection[1]} in ${selected.relative_path}.`,
                  );
                  setPanel("chat");
                  setTab("chat");
                }}
              >
                Explain selection →
              </button>
            )}
          </div>
        </section>
        <div
          role="separator"
          aria-label="Resize answer panel"
          aria-orientation="vertical"
          tabIndex={0}
          className="resize-handle"
          onKeyDown={(e) => {
            if (["ArrowLeft", "ArrowRight"].includes(e.key)) {
              e.preventDefault();
              setWidth((w) =>
                Math.max(
                  320,
                  Math.min(560, w + (e.key === "ArrowLeft" ? 20 : -20)),
                ),
              );
            }
          }}
          onPointerDown={(e) => {
            const node = e.currentTarget;
            node.setPointerCapture(e.pointerId);
            const start = e.clientX,
              initial = width;
            node.onpointermove = (ev) =>
              setWidth(
                Math.max(320, Math.min(560, initial + start - ev.clientX)),
              );
            node.onpointerup = () => {
              node.onpointermove = null;
            };
          }}
        />
        <aside
          className={`chat-pane ${tab === "chat" || tab === "guide" ? "mobile-visible" : ""}`}
        >
          <div className="chat-tabs">
            <button
              className={panel === "chat" ? "active" : ""}
              onClick={() => setPanel("chat")}
            >
              <Icon name="chat" />
              Ask CodeBuddy
            </button>
            <button
              className={panel === "guide" ? "active" : ""}
              onClick={() => setPanel("guide")}
            >
              <Icon name="book" />
              Guide
            </button>
          </div>
          <div className="chat-scroll">
            {panel === "guide" ? (
              <>
                {!demo && sid !== project.data?.active_snapshot_id && (
                  <p className="notice">
                    This guide belongs to an older snapshot. Switch to the
                    latest snapshot for current source.
                  </p>
                )}
                <div className="chat-intro">
                  <Icon name="book" />
                  <h2>A map of your code.</h2>
                  <p>
                    Purpose, key files, and a grounded reading order for this
                    snapshot.
                  </p>
                </div>
                {guide && (
                  <>
                    <Answer answer={guide} onCitation={cite} />
                    <button
                      className="button ghost"
                      onClick={() =>
                        navigator.clipboard
                          .writeText(
                            `Snapshot: ${sid}\n\n` +
                              guide.claims.map((c: any) => c.text).join("\n\n"),
                          )
                          .then(() => setFeedback("Guide copied."))
                          .catch(() =>
                            setFeedback("Copy unavailable in this browser."),
                          )
                      }
                    >
                      Copy guide
                    </button>
                  </>
                )}{" "}
                {!demo && (
                  <>
                    <button
                      className="button ghost"
                      disabled={!!job}
                      onClick={async () => {
                        try {
                          const j = await post(
                            `/projects/${projectId}/guides?snapshot_id=${sid}`,
                            {},
                            crypto.randomUUID(),
                          );
                          setJob(j.id);
                        } catch (e) {
                          setError((e as Error).message);
                        }
                      }}
                    >
                      {guide
                        ? "Generate new version"
                        : "Generate onboarding guide"}
                    </button>
                    {guides.data?.items?.[0] && (
                      <a
                        className="text-link"
                        href={`/api/v1/guides/${guides.data.items[0].id}/export`}
                      >
                        Download Markdown ↓
                      </a>
                    )}
                  </>
                )}
              </>
            ) : (
              <>
                {((demo && !demoAnswer) ||
                  (!demo && !messages.data?.length)) && (
                  <div className="chat-intro">
                    <div className="assistant-mark">✳</div>
                    <h2>Get to know this codebase.</h2>
                    <p>
                      Ask a question. Follow the evidence.
                      <br />
                      Build your understanding.
                    </p>
                  </div>
                )}
                {demo ? (
                  <>
                    <div className="suggestions">
                      {demoData.answers
                        .filter((a) => a.id !== "onboarding")
                        .map((a) => (
                          <button key={a.id} onClick={() => setDemoAnswer(a)}>
                            {a.question}
                            <Icon name="arrow" />
                          </button>
                        ))}
                    </div>
                    {demoAnswer && (
                      <Answer answer={demoAnswer} onCitation={cite} />
                    )}
                  </>
                ) : (
                  <>
                    {messages.data?.map((m: any) => (
                      <div className={`message ${m.role}`} key={m.id}>
                        <div className="message-heading">
                          {m.role === "user" ? "You" : "CodeBuddy"}
                        </div>
                        {m.role === "user" ? (
                          <p>{m.content.text}</p>
                        ) : (
                          <>
                            <Answer answer={m.content} onCitation={cite} />
                            <div className="message-actions">
                              <button
                                onClick={() =>
                                  navigator.clipboard.writeText(
                                    m.content.claims
                                      .map((c: any) => c.text)
                                      .join("\n\n"),
                                  )
                                }
                              >
                                Copy
                              </button>
                              <button
                                onClick={() =>
                                  post(`/messages/${m.id}/feedback`, {
                                    rating: 1,
                                  })
                                    .then(() =>
                                      setFeedback("Feedback saved. Thank you."),
                                    )
                                    .catch((e) => setError(e.message))
                                }
                                aria-label="Helpful answer"
                              >
                                Helpful
                              </button>
                              <button
                                onClick={() =>
                                  post(`/messages/${m.id}/feedback`, {
                                    rating: -1,
                                  })
                                    .then(() =>
                                      setFeedback("Feedback saved. Thank you."),
                                    )
                                    .catch((e) => setError(e.message))
                                }
                                aria-label="Unhelpful answer"
                              >
                                Not helpful
                              </button>
                              <button
                                onClick={async () => {
                                  try {
                                    setJob(
                                      (
                                        await post(
                                          `/messages/${m.id}/regenerate`,
                                          {},
                                          crypto.randomUUID(),
                                        )
                                      ).id,
                                    );
                                  } catch (e) {
                                    setError((e as Error).message);
                                  }
                                }}
                              >
                                Regenerate
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    ))}
                    {!conversation && (
                      <div className="suggestions">
                        {[
                          "What does this project do?",
                          "Where does authentication happen?",
                          "Which files should I read first?",
                        ].map((q) => (
                          <button key={q} onClick={() => setQuestion(q)}>
                            {q}
                            <Icon name="arrow" />
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </>
            )}
            {job && <JobStatus id={job} onDone={finished} />}{" "}
            {feedback && (
              <p role="status" className="muted small">
                {feedback}
              </p>
            )}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            {!job &&
              project.data?.jobs
                ?.filter(
                  (j: any) => j.kind === "ingestion" && j.snapshot_id === sid,
                )
                .slice(0, 1)
                .map((j: any) => (
                  <JobStatus
                    key={j.id}
                    id={j.id}
                    onDone={() => {
                      cache.invalidateQueries({
                        queryKey: ["project", projectId],
                      });
                      cache.invalidateQueries({
                        queryKey: ["files", projectId],
                      });
                    }}
                  />
                ))}
            {project.error && <p className="error">{project.error.message}</p>}
            {fileQuery.error && (
              <p className="error">{fileQuery.error.message}</p>
            )}
          </div>
          {!demo && panel === "chat" && (
            <form
              className="composer"
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
            >
              {selection && (
                <button
                  type="button"
                  className="selection-chip"
                  onClick={() => setSelection(null)}
                >
                  Lines {selection[0]}–{selection[1]} ×
                </button>
              )}
              <textarea
                aria-label="Ask a question"
                placeholder="Ask about your code…"
                maxLength={6000}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                rows={3}
              />
              <div>
                <span>Answers grounded in this snapshot</span>
                <button
                  className="send-button"
                  aria-label="Send question"
                  disabled={busy || !!job || !question.trim()}
                >
                  ↑
                </button>
              </div>
            </form>
          )}
          {demo && (
            <div className="demo-chat-note">
              Precomputed answers · No live AI calls
            </div>
          )}
        </aside>
      </div>
      {!demo && (
        <details className="workspace-search">
          <summary>Search repository</summary>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                setResults(
                  (
                    await api(
                      `/projects/${projectId}/search?snapshot_id=${sid}&q=${encodeURIComponent(search)}`,
                    )
                  ).items,
                );
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            <input
              aria-label="Repository search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button className="button ghost">Search</button>
          </form>
          {results.map((c) => (
            <button key={c.source_id} onClick={() => cite(c)}>
              {c.path}:{c.start_line}–{c.end_line}
            </button>
          ))}
        </details>
      )}
    </div>
  );
}
