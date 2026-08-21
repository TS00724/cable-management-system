export interface PageResult<T> {
  items: T[];
  total: number;
}

export interface DashboardData {
  tenant_id: string;
  counts?: Record<string, number>;
  [key: string]: unknown;
}

export interface LocationRecord {
  id: string;
  identifier: string;
  name: string;
  location_type: string;
  parent_id?: string | null;
  status?: string;
}

export interface RackRecord {
  id: string;
  rack_identifier?: string;
  identifier?: string;
  name: string;
  height_u?: number;
  location_id?: string;
}

export interface CableRecord {
  id: string;
  identifier: string;
  media_type: string;
  construction?: string;
  installation_status?: string;
  test_status?: string;
}

export interface TraceResult {
  complete: boolean;
  nodes?: Array<Record<string, unknown>>;
  path?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}
