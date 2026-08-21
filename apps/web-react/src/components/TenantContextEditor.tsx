import { Button, Drawer, Form, Input, Space } from "antd";
import { useEffect, useState } from "react";
import type { InfrastructureContext } from "../api/context";

export function TenantContextEditor({ value, onChange }: { value: InfrastructureContext; onChange: (value: InfrastructureContext) => void }) {
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm<InfrastructureContext>();
  useEffect(() => { form.setFieldsValue(value); }, [form, value]);
  return <>
    <Button onClick={() => setOpen(true)}>Tenant context</Button>
    <Drawer title="Request context" open={open} onClose={() => setOpen(false)} width={420}>
      <Form form={form} layout="vertical" onFinish={(next) => { onChange(next); setOpen(false); }}>
        <Form.Item name="tenantId" label="Tenant UUID" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="actorId" label="Demo actor UUID"><Input /></Form.Item>
        <Form.Item name="projectId" label="Project UUID"><Input /></Form.Item>
        <Form.Item name="locationId" label="Location UUID"><Input /></Form.Item>
        <Space><Button htmlType="submit" type="primary">Apply</Button><Button onClick={() => setOpen(false)}>Cancel</Button></Space>
      </Form>
    </Drawer>
  </>;
}
