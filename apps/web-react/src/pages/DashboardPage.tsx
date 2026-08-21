import { Card, Col, Row, Statistic, Typography } from "antd";
import type { InfrastructureContext } from "../api/context";
import { createApiClient } from "../api/client";
import type { DashboardData } from "../types";
import { useApiResource } from "../components/useApiResource";
import { AsyncState } from "./AsyncState";

export function DashboardPage({ getContext }: { getContext: () => InfrastructureContext }) {
  const api = createApiClient({ getContext });
  const state = useApiResource(() => api.request<DashboardData>("/dashboard"), [getContext().tenantId]);
  const counts = state.data?.counts ?? Object.fromEntries(Object.entries(state.data ?? {}).filter(([, value]) => typeof value === "number")) as Record<string, number>;
  return <><Typography.Title level={2}>Dashboard</Typography.Title><AsyncState loading={state.loading} error={state.error} empty={!state.data}>{<Row gutter={[16, 16]}>{Object.entries(counts).map(([label, value]) => <Col xs={24} sm={12} lg={6} key={label}><Card><Statistic title={label.replaceAll("_", " ")} value={value} /></Card></Col>)}</Row>}</AsyncState></>;
}
