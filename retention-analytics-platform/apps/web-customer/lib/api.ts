const API_BASE = typeof window !== "undefined"
  ? (process.env.NEXT_PUBLIC_API_URL || "/api/v1")
  : (process.env.API_BACKEND_URL || "http://api:47319") + "/api/v1";

export function authHeaders(): Record<string, string> {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("auth_token") ||
        (process.env.NEXT_PUBLIC_DEV_TOKEN as string | undefined) ||
        "dev-token"
      : (process.env.INTERNAL_API_TOKEN as string | undefined) || "dev-token";
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export async function apiGet(path: string): Promise<any> {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export async function apiPost(
  path: string,
  body?: unknown,
): Promise<any> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}