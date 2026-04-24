import { DocumentDashboard } from "@/components/document-dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function HomePage() {
  return <DocumentDashboard apiBaseUrl={API_BASE_URL} />;
}