import { writeAccessToken } from "./tokenStore";

const VERIFIER_KEY = "sim.oidc.pkce-verifier";

function base64Url(input: ArrayBuffer): string {
  const bytes = new Uint8Array(input);
  let binary = "";
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

export function randomVerifier(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(48));
  return base64Url(bytes.buffer);
}

export async function challengeFor(verifier: string): Promise<string> {
  return base64Url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
}

export async function startOidcLogin(): Promise<void> {
  const issuer = import.meta.env.VITE_OIDC_ISSUER as string | undefined;
  const clientId = import.meta.env.VITE_OIDC_CLIENT_ID as string | undefined;
  if (!issuer || !clientId) throw new Error("OIDC issuer/client ID are not configured");
  const verifier = randomVerifier();
  sessionStorage.setItem(VERIFIER_KEY, verifier);
  const callback = `${window.location.origin}/app-next/oidc/callback`;
  const url = new URL(`${issuer.replace(/\/$/, "")}/protocol/openid-connect/auth`);
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", callback);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", "openid profile email");
  url.searchParams.set("code_challenge", await challengeFor(verifier));
  url.searchParams.set("code_challenge_method", "S256");
  window.location.assign(url.toString());
}

export async function finishOidcLogin(code: string): Promise<void> {
  const issuer = import.meta.env.VITE_OIDC_ISSUER as string | undefined;
  const clientId = import.meta.env.VITE_OIDC_CLIENT_ID as string | undefined;
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  if (!issuer || !clientId || !verifier) throw new Error("OIDC callback state is incomplete");
  const callback = `${window.location.origin}/app-next/oidc/callback`;
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: clientId,
    code,
    redirect_uri: callback,
    code_verifier: verifier,
  });
  const response = await fetch(`${issuer.replace(/\/$/, "")}/protocol/openid-connect/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) throw new Error("OIDC token exchange failed");
  const payload = await response.json() as { access_token?: string };
  if (!payload.access_token) throw new Error("OIDC response has no access token");
  writeAccessToken(payload.access_token);
  sessionStorage.removeItem(VERIFIER_KEY);
}
