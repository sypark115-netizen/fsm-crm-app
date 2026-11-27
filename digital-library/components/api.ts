"use client";
// 클라이언트 → 로컬 API 호출 헬퍼

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((body as { error?: string }).error ?? `요청 실패 (${res.status})`);
  return body as T;
}

export const api = {
  get: <T,>(url: string) => call<T>(url),
  post: <T,>(url: string, data: unknown) => call<T>(url, { method: "POST", body: JSON.stringify(data) }),
  patch: <T,>(url: string, data: unknown) => call<T>(url, { method: "PATCH", body: JSON.stringify(data) }),
  put: <T,>(url: string, data: unknown) => call<T>(url, { method: "PUT", body: JSON.stringify(data) }),
  del: <T,>(url: string) => call<T>(url, { method: "DELETE" }),
};
