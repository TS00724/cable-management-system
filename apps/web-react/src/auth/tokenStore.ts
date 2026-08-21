const TOKEN_KEY = "sim.oidc.access-token";

export function readAccessToken(storage: Pick<Storage, "getItem"> = window.sessionStorage): string | null {
  return storage.getItem(TOKEN_KEY);
}

export function writeAccessToken(
  token: string,
  storage: Pick<Storage, "setItem"> = window.sessionStorage,
): void {
  storage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken(storage: Pick<Storage, "removeItem"> = window.sessionStorage): void {
  storage.removeItem(TOKEN_KEY);
}

export function hasUsableToken(token: string | null): boolean {
  return typeof token === "string" && token.trim().split(".").length === 3;
}
