import { Alert, Spin } from "antd";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { finishOidcLogin } from "../auth/oidc";
export function OidcCallbackPage() { const [params] = useSearchParams(); const navigate = useNavigate(); const [error, setError] = useState<string>(); useEffect(() => { const code = params.get("code"); if (!code) { setError("OIDC callback has no authorization code"); return; } void finishOidcLogin(code).then(() => navigate("/", { replace: true })).catch((caught) => setError(caught instanceof Error ? caught.message : String(caught))); }, [navigate, params]); return error ? <Alert type="error" message="Sign-in failed" description={error} /> : <Spin fullscreen tip="Completing sign-in" />; }
