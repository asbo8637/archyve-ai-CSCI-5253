import type { Metadata } from "next";

import { Auth0ProviderClient } from "@/components/auth0-provider";
import { getWebRuntimeConfig } from "@/lib/runtime-config";

import "./globals.css";

export const metadata: Metadata = {
  title: "Archyve AI",
  description: "Secure, company-scoped document workflows for B2B teams."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  const config = getWebRuntimeConfig();
  const content = config.authConfigured ? (
    <Auth0ProviderClient
      audience={config.auth0Audience}
      clientId={config.auth0ClientId}
      domain={config.auth0Domain}
    >
      {children}
    </Auth0ProviderClient>
  ) : (
    children
  );

  return (
    <html lang="en">
      <body>{content}</body>
    </html>
  );
}
