import { contextHeaders, type InfrastructureContext } from "./context";
import { readAccessToken } from "../auth/tokenStore";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly requestId?: string,
    readonly body?: unknown,
  ) { super(message); }
}

export interface ApiClientOptions {
  baseUrl?: string;
  getContext: () => InfrastructureContext;
}

export function createApiClient(options: ApiClientOptions) {
  const baseUrl = (options.baseUrl ?? "/api/v1").replace(/\/$/, "");

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    Object.entries(contextHeaders(options.getContext())).forEach(([key, value]) => headers.set(key, value));
    const token = readAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    const response = await fetch(`${baseUrl}${path}`, { ...init, headers });
    const contentType = response.headers.get("content-type") ?? "";
    const body = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = typeof body === "object" && body && "detail" in body ? String((body as { detail: unknown }).detail) : response.statusText;
      throw new ApiError(detail || "API request failed", response.status, response.headers.get("x-request-id") ?? undefined, body);
    }
    return body as T;
  }

  async function download(path: string): Promise<Blob> {
    const headers = new Headers(contextHeaders(options.getContext()));
    const token = readAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(`${baseUrl}${path}`, { headers });
    if (!response.ok) throw new ApiError("Download failed", response.status, response.headers.get("x-request-id") ?? undefined);
    return response.blob();
  }

  return { request, download };
}
