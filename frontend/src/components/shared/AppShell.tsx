"use client";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import Link from "next/link";
import Brand from "./Brand";
import Icon from "./Icon";
import { api, ApiError, post } from "@/lib/api";
export default function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [logoutError, setLogoutError] = useState("");
  const auth = useQuery({
    queryKey: ["me"],
    queryFn: () => api("/auth/me"),
    retry: false,
  });
  useEffect(() => {
    if (auth.error instanceof ApiError && auth.error.status === 401)
      location.replace(`/login?next=${encodeURIComponent(path)}`);
  }, [auth.error, path]);
  if (auth.isPending)
    return <main className="loading">Opening your workspace…</main>;
  if (auth.error)
    return (
      <main className="loading">
        <p role="alert">{auth.error.message}</p>
        <button className="button ghost" onClick={() => auth.refetch()}>
          Try again
        </button>
        <Link href="/demo">Explore the offline demo</Link>
      </main>
    );
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <Brand />
        <nav>
          <Link className={path === "/app" ? "active" : ""} href="/app">
            <Icon name="folder" />
            My projects
          </Link>
          <Link href="/app/new">
            <Icon name="plus" />
            New project
          </Link>
          <Link href="/demo">
            <Icon name="book" />
            Explore demo
          </Link>
        </nav>
        <div className="sidebar-bottom">
          <Link href="/app/settings">
            <Icon name="settings" />
            {auth.data.user.display_name}
          </Link>
          <button
            onClick={async () => {
              try {
                setLogoutError("");
                await post("/auth/logout");
                location.assign("/login");
              } catch (e) { setLogoutError((e as Error).message); }
            }}
          >
            Sign out
          </button>
          {logoutError && <p className="error" role="alert">{logoutError}</p>}
          <p className="creator-credit">Powered by Malik Ismail Manzoor</p>
        </div>
      </aside>
      <div className="app-content">
        {!auth.data.ai_available && (
          <div className="notice">
            Live AI is unavailable. Configure the server’s Gemini key to index
            and ask questions. Demo and source previews remain available.
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
