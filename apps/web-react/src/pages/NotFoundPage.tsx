import { Result, Button } from "antd";
import { Link } from "react-router-dom";
export function NotFoundPage() { return <Result status="404" title="404" subTitle="The infrastructure page does not exist." extra={<Link to="/"><Button type="primary">Dashboard</Button></Link>} />; }
