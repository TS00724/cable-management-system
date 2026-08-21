import { Card, Table, Typography } from "antd";
import type { InfrastructureContext } from "../api/context";
import { createApiClient } from "../api/client";
import type { LocationRecord, PageResult } from "../types";
import { useApiResource } from "../components/useApiResource";
import { AsyncState } from "./AsyncState";

export function LocationsPage({ getContext }: { getContext: () => InfrastructureContext }) {
  const api = createApiClient({ getContext });
  const state = useApiResource(async () => {
    const result = await api.request<LocationRecord[] | PageResult<LocationRecord>>("/locations");
    return Array.isArray(result) ? result : result.items;
  }, [getContext().tenantId]);
  return <><Typography.Title level={2}>Locations</Typography.Title><Card><AsyncState loading={state.loading} error={state.error} empty={!state.data?.length}><Table rowKey="id" size="small" pagination={{ pageSize: 25 }} dataSource={state.data} columns={[{ title: "Identifier", dataIndex: "identifier" }, { title: "Name", dataIndex: "name" }, { title: "Type", dataIndex: "location_type" }, { title: "Status", dataIndex: "status" }]} /></AsyncState></Card></>;
}
