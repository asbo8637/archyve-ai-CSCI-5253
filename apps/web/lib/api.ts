import type { DocumentRecord } from "@/lib/documents";

export type AccessTokenGetter = () => Promise<string>;

export type AuthSession = {
  active_company: {
    id: string;
    name: string;
    role: string;
  } | null;
  company_selection_required: boolean;
  memberships: Array<{
    company_id: string;
    company_name: string;
    role: string;
    status: string;
  }>;
  needs_company_setup: boolean;
  permissions: string[];
  user: {
    auth0_user_id: string;
    email: string | null;
    full_name: string | null;
    id: string;
    status: string;
  };
};

type ApiDetail =
  | string
  | {
      code?: string;
      message?: string;
    };

type ApiErrorResponse = {
  detail?: ApiDetail;
};

export class ApiError extends Error {
  code?: string;
  status: number;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.code = code;
    this.name = "ApiError";
    this.status = status;
  }
}

type ApiRequestInit = Omit<RequestInit, "headers"> & {
  headers?: HeadersInit;
};

export async function getAuthSession(
  apiBaseUrl: string,
  getAccessToken: AccessTokenGetter
): Promise<AuthSession> {
  return apiRequest<AuthSession>(apiBaseUrl, "/auth/session", getAccessToken);
}

export async function createCompany(
  apiBaseUrl: string,
  getAccessToken: AccessTokenGetter,
  name: string
): Promise<AuthSession> {
  return apiRequest<AuthSession>(
    apiBaseUrl,
    "/auth/onboarding/create-company",
    getAccessToken,
    {
      body: JSON.stringify({ name }),
      method: "POST"
    }
  );
}

export async function selectCompany(
  apiBaseUrl: string,
  getAccessToken: AccessTokenGetter,
  companyId: string
): Promise<AuthSession> {
  return apiRequest<AuthSession>(
    apiBaseUrl,
    "/auth/session/select-company",
    getAccessToken,
    {
      body: JSON.stringify({ company_id: companyId }),
      method: "POST"
    }
  );
}

export async function getDocuments(
  apiBaseUrl: string,
  getAccessToken: AccessTokenGetter
): Promise<DocumentRecord[]> {
  return apiRequest<DocumentRecord[]>(apiBaseUrl, "/documents", getAccessToken);
}

export async function uploadDocument(
  apiBaseUrl: string,
  getAccessToken: AccessTokenGetter,
  file: File
): Promise<DocumentRecord> {
  const payload = new FormData();
  payload.append("file", file);

  return apiRequest<DocumentRecord>(apiBaseUrl, "/documents", getAccessToken, {
    body: payload,
    method: "POST"
  });
}

async function apiRequest<T>(
  apiBaseUrl: string,
  path: string,
  getAccessToken: AccessTokenGetter,
  init: ApiRequestInit = {}
): Promise<T> {
  const token = await getAccessToken();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);

  if (!(init.body instanceof FormData) && init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorResponse | null;
    throw buildApiError(response.status, body);
  }

  return (await response.json()) as T;
}

function buildApiError(status: number, body: ApiErrorResponse | null): ApiError {
  const detail = body?.detail;

  if (typeof detail === "string") {
    return new ApiError(detail, status);
  }

  if (detail && typeof detail === "object") {
    return new ApiError(
      detail.message ?? "The request failed.",
      status,
      detail.code
    );
  }

  return new ApiError("The request failed.", status);
}
