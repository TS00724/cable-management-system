import { Alert, Empty, Skeleton } from "antd";
import type { PropsWithChildren } from "react";

export function AsyncState({ loading, error, empty, children }: PropsWithChildren<{ loading: boolean; error?: Error; empty?: boolean }>) {
  if (loading) return <Skeleton active paragraph={{ rows: 8 }} />;
  if (error) return <Alert type="error" showIcon message="API request failed" description={error.message} />;
  if (empty) return <Empty description="No records in the selected tenant context" />;
  return <>{children}</>;
}
