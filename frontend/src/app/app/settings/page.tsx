"use client";
import { useState } from "react";
import { api } from "@/lib/api";
export default function Settings() {
  const [name, setName] = useState(""),
    [password, setPassword] = useState(""),
    [message, setMessage] = useState("");
  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/account", {
        method: "PATCH",
        body: JSON.stringify({ display_name: name, password }),
      });
      setMessage("Account updated.");
    } catch (e) {
      setMessage((e as Error).message);
    }
  }
  return (
    <main className="narrow-page">
      <p className="eyebrow">ACCOUNT</p>
      <h1>Settings</h1>
      <form onSubmit={save}>
        <label>
          Display name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={100}
          />
        </label>
        <label>
          Current password
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <button className="button solid">Save changes</button>
      </form>
      <p role="status">{message}</p>
      <div className="danger-zone">
        <h2>Delete account</h2>
        <p>
          Remove your projects, source snapshots, conversations, and account.
          Backups follow your operator’s retention policy.
        </p>
        <button
          className="button ghost danger"
          onClick={async () => {
            if (!confirm("Permanently delete your account and all projects?"))
              return;
            try {
              await api("/account", {
                method: "DELETE",
                body: JSON.stringify({ password }),
              });
              location.assign("/");
            } catch (e) {
              setMessage((e as Error).message);
            }
          }}
        >
          Delete my account
        </button>
      </div>
    </main>
  );
}
