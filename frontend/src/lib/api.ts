let csrf = "";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function api<T = any>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = init.method || "GET";
  if (method !== "GET" && !csrf) {
    const r = await fetch("/api/v1/auth/csrf", { credentials: "same-origin" });
    csrf = (await r.json()).csrf_token;
  }
  const headers = new Headers(init.headers);
  if (method !== "GET") headers.set("X-CSRFToken", csrf);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      response.status === 413
        ? "The ZIP exceeds the upload capacity. Upload a source-only ZIP under 100 MiB, excluding dependencies, build outputs, and videos."
        : "The service is unavailable. Please retry shortly or ask your administrator to check the API.",
      response.status || 503,
    );
  }
  if (!response.ok) {
    if (response.status === 400) csrf = "";
    throw new ApiError(
      data.error?.message || "Request failed. Please retry.",
      response.status,
    );
  }
  if (data.csrf_token) csrf = data.csrf_token;
  if (path === "/auth/logout" || (path === "/account" && method === "DELETE"))
    csrf = "";
  return data as T;
}
export function post(path: string, data: unknown = {}, key?: string) {
  return api(path, {
    method: "POST",
    body: JSON.stringify(data),
    headers: key ? { "Idempotency-Key": key } : {},
  });
}
export function safeReturn(value: string | null) {
  return (value === "/app" || value?.startsWith("/app/")) &&
    !value.includes("\\") &&
    !value.includes(":")
    ? value
    : "/app";
}
export async function allPages(path: string) {
  const items: any[] = [];
  for (let offset = 0; offset < 5000; offset += 100) {
    const page = await api(
      `${path}${path.includes("?") ? "&" : "?"}limit=100&offset=${offset}`,
    );
    items.push(...page.items);
    if (page.items.length < 100) break;
  }
  return items;
}
