import { describe, expect, it } from "vitest";
import { contextHeaders, normalizeContext } from "./context";
import { hasUsableToken } from "../auth/tokenStore";

describe("client context helpers", () => {
  it("normalizes and emits scoped headers", () => {
    const context = normalizeContext({ tenantId: " tenant ", actorId: " actor ", projectId: "" });
    expect(contextHeaders(context)).toEqual({ "X-Tenant-ID": "tenant", "X-Actor-ID": "actor" });
  });
  it("recognizes JWT-shaped access tokens without trusting their claims", () => {
    expect(hasUsableToken("a.b.c")).toBe(true);
    expect(hasUsableToken("opaque")).toBe(false);
  });
});
