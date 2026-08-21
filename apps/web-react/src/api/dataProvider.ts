import type { DataProvider } from "@refinedev/core";
import type { InfrastructureContext } from "./context";
import { createApiClient } from "./client";

export function buildDataProvider(getContext: () => InfrastructureContext): DataProvider {
  const api = createApiClient({ getContext });
  return {
    getApiUrl: () => "/api/v1",
    getList: async ({ resource }) => {
      const result = await api.request<unknown[] | { items: unknown[]; total?: number }>(`/${resource}`);
      const data = Array.isArray(result) ? result : result.items;
      return { data, total: Array.isArray(result) ? result.length : (result.total ?? data.length) };
    },
    getOne: async ({ resource, id }) => ({ data: await api.request(`/${resource}/${id}`) }),
    create: async ({ resource, variables }) => ({
      data: await api.request(`/${resource}`, { method: "POST", body: JSON.stringify(variables) }),
    }),
    update: async ({ resource, id, variables }) => ({
      data: await api.request(`/${resource}/${id}`, { method: "PATCH", body: JSON.stringify(variables) }),
    }),
    deleteOne: async ({ resource, id }) => ({
      data: await api.request(`/${resource}/${id}`, { method: "DELETE" }),
    }),
    custom: async ({ url, method = "get", payload }) => ({
      data: await api.request(url.replace(/^\/api\/v1/, ""), {
        method: method.toUpperCase(),
        body: payload === undefined ? undefined : JSON.stringify(payload),
      }),
    }),
  } as DataProvider;
}
