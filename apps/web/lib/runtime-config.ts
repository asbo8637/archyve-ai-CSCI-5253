export type WebRuntimeConfig = {
  apiBaseUrl: string;
  auth0Audience: string;
  auth0ClientId: string;
  auth0Domain: string;
  authConfigured: boolean;
};

export function getWebRuntimeConfig(): WebRuntimeConfig {
  const auth0Domain =
    process.env.NEXT_PUBLIC_AUTH0_DOMAIN ?? process.env.AUTH0_DOMAIN ?? "";
  const auth0ClientId = resolveAuth0ClientId();
  const auth0Audience =
    process.env.NEXT_PUBLIC_AUTH0_AUDIENCE ??
    process.env.AUTH0_AUDIENCE ??
    process.env.API_AUDIENCE ??
    "";
  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  return {
    apiBaseUrl,
    auth0Audience,
    auth0ClientId,
    auth0Domain,
    authConfigured:
      auth0Domain.length > 0 &&
      auth0ClientId.length > 0 &&
      auth0Audience.length > 0
  };
}

function resolveAuth0ClientId(): string {
  const publicClientId = process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID ?? "";
  const applicationClientId = process.env.AUTH0_CLIENT_ID ?? "";
  const managementClientId = process.env.AUTH0_MGMT_CLIENT_ID ?? "";

  if (publicClientId && publicClientId !== managementClientId) {
    return publicClientId;
  }

  if (applicationClientId) {
    return applicationClientId;
  }

  return publicClientId;
}
