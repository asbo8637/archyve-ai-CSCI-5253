import { DocumentDashboard } from "@/components/document-dashboard";
import { getWebRuntimeConfig } from "@/lib/runtime-config";

export default function HomePage() {
  const config = getWebRuntimeConfig();

  return (
    <DocumentDashboard
      apiBaseUrl={config.apiBaseUrl}
      authConfigured={config.authConfigured}
    />
  );
}
