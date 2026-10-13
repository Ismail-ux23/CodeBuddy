import { afterEach, expect, it, vi } from "vitest";

afterEach(() => { vi.unstubAllGlobals(); vi.resetModules(); });

it("fetches a fresh CSRF token after logout before another login", async () => {
  const { post } = await import("../src/lib/api");
  const fetcher = vi.fn()
    .mockResolvedValueOnce(Response.json({csrf_token: "first-token"}))
    .mockResolvedValueOnce(Response.json({user: {}, csrf_token: "signed-in-token"}))
    .mockResolvedValueOnce(Response.json({ok: true}))
    .mockResolvedValueOnce(Response.json({csrf_token: "new-session-token"}))
    .mockResolvedValueOnce(Response.json({user: {}}));
  vi.stubGlobal("fetch", fetcher);
  await post("/auth/login", {email: "me@example.com", password: "password"});
  await post("/auth/logout");
  await post("/auth/login", {email: "me@example.com", password: "password"});
  expect(fetcher).toHaveBeenCalledTimes(5);
  expect(fetcher.mock.calls[3][0]).toBe("/api/v1/auth/csrf");
  expect(fetcher.mock.calls[4][1].headers.get("X-CSRFToken")).toBe("new-session-token");
});
