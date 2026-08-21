export interface InfrastructureContext {
  tenantId: string;
  actorId?: string;
  projectId?: string;
  locationId?: string;
}

const STORAGE_KEY = "sim.infrastructure-context";

export function normalizeContext(value: Partial<InfrastructureContext>): InfrastructureContext {
  return {
    tenantId: value.tenantId?.trim() ?? "",
    actorId: value.actorId?.trim() || undefined,
    projectId: value.projectId?.trim() || undefined,
    locationId: value.locationId?.trim() || undefined,
  };
}

export function loadContext(storage: Pick<Storage, "getItem"> = window.localStorage): InfrastructureContext {
  const raw = storage.getItem(STORAGE_KEY);
  if (!raw) return { tenantId: "" };
  try {
    return normalizeContext(JSON.parse(raw) as Partial<InfrastructureContext>);
  } catch {
    return { tenantId: "" };
  }
}

export function saveContext(
  context: InfrastructureContext,
  storage: Pick<Storage, "setItem"> = window.localStorage,
): InfrastructureContext {
  const normalized = normalizeContext(context);
  storage.setItem(STORAGE_KEY, JSON.stringify(normalized));
  return normalized;
}

export function contextHeaders(context: InfrastructureContext): Record<string, string> {
  const headers: Record<string, string> = {};
  if (context.tenantId) headers["X-Tenant-ID"] = context.tenantId;
  if (context.actorId) headers["X-Actor-ID"] = context.actorId;
  if (context.projectId) headers["X-Project-ID"] = context.projectId;
  if (context.locationId) headers["X-Location-ID"] = context.locationId;
  return headers;
}
