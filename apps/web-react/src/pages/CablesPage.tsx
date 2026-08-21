import { Button, Card, Drawer, Space, Table, Tag, Typography } from "antd";
import { DownloadOutlined, NodeIndexOutlined } from "@ant-design/icons";
import { useState } from "react";
import type { InfrastructureContext } from "../api/context";
import { createApiClient } from "../api/client";
import type { CableRecord, PageResult, TraceResult } from "../types";
import { useApiResource } from "../components/useApiResource";
import { AsyncState } from "./AsyncState";

export function CablesPage({ getContext }: { getContext: () => InfrastructureContext }) {
  const api = createApiClient({ getContext });
  const [traceCable, setTraceCable] = useState<CableRecord>();
  const state = useApiResource(async () => {
    const result = await api.request<CableRecord[] | PageResult<CableRecord>>("/cables");
    return Array.isArray(result) ? result : result.items;
  }, [getContext().tenantId]);
  const trace = useApiResource(() => traceCable ? api.request<TraceResult>(`/cables/${traceCable.id}/trace`) : Promise.resolve({ complete: false }), [traceCable?.id]);
  const exportSchedule = async () => {
    const blob = await api.download("/reports/cable-schedule.csv");
    const url = URL.createObjectURL(blob); const anchor = document.createElement("a");
    anchor.href = url; anchor.download = "cable-schedule.csv"; anchor.click(); URL.revokeObjectURL(url);
  };
  return <><Space className="page-title"><Typography.Title level={2}>Cables</Typography.Title><Button icon={<DownloadOutlined />} onClick={() => void exportSchedule()}>Cable Schedule CSV</Button></Space><Card><AsyncState loading={state.loading} error={state.error} empty={!state.data?.length}><Table rowKey="id" size="small" dataSource={state.data} columns={[{ title: "Identifier", dataIndex: "identifier" }, { title: "Media", dataIndex: "media_type" }, { title: "Construction", dataIndex: "construction" }, { title: "Status", dataIndex: "installation_status", render: (value) => <Tag>{value ?? "unknown"}</Tag> }, { title: "", render: (_, row: CableRecord) => <Button icon={<NodeIndexOutlined />} onClick={() => setTraceCable(row)}>Trace</Button> }]} /></AsyncState></Card><Drawer width={720} title={`Cable Trace — ${traceCable?.identifier ?? ""}`} open={Boolean(traceCable)} onClose={() => setTraceCable(undefined)}><AsyncState loading={trace.loading} error={trace.error} empty={!traceCable}><pre className="trace-json">{JSON.stringify(trace.data, null, 2)}</pre></AsyncState></Drawer></>;
}
