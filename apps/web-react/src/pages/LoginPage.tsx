import { Button, Card, Typography } from "antd";
import { startOidcLogin } from "../auth/oidc";
export function LoginPage() { return <Card className="login-card"><Typography.Title level={2}>Enterprise sign in</Typography.Title><Typography.Paragraph>Use the configured OIDC / Keycloak identity provider. Tenant access remains enforced by the API.</Typography.Paragraph><Button type="primary" onClick={() => void startOidcLogin()}>Sign in with OIDC</Button></Card>; }
