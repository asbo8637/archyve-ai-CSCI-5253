"use client";

import { Auth0Provider } from "@auth0/auth0-react";

type Auth0ProviderClientProps = {
  audience: string;
  children: React.ReactNode;
  clientId: string;
  domain: string;
};

export function Auth0ProviderClient({
  audience,
  children,
  clientId,
  domain
}: Auth0ProviderClientProps) {
  const redirectUri =
    typeof window === "undefined" ? undefined : window.location.origin;

  return (
    <Auth0Provider
      authorizationParams={{
        audience,
        redirect_uri: redirectUri,
        scope: "openid profile email offline_access"
      }}
      clientId={clientId}
      domain={domain}
      useRefreshTokens
    >
      {children}
    </Auth0Provider>
  );
}
