import type { DocumentRecord } from "@/lib/documents";

export type AuthTokenBundle = {
  accessToken: string;
  idToken?: string;
};
export type AuthTokenGetter = () => Promise<AuthTokenBundle>;
export type AccessTokenGetter = AuthTokenGetter;

export type AuthSession = {
  active_company: {
    id: string;
    location_label: string | null;
    name: string;
    role: string;
  } | null;
  company_selection_required: boolean;
  memberships: Array<{
    company_id: string;
    company_name: string;
    location_label: string | null;
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

export type CompanyRole = "admin" | "manager" | "employee" | "trainee";

export type CompanyMembership = {
  id: string;
  user_id: string;
  email: string | null;
  full_name: string | null;
  role: CompanyRole;
  status: string;
  location_label: string | null;
};

export type UpsertCompanyMembershipInput = {
  email: string;
  full_name?: string | null;
  role: CompanyRole;
  location_label?: string | null;
};

export type ChatCitation = {
  source_label: string;
  text: string | null;
  document_id: string | null;
  document_name: string | null;
};

export type ChatAnswer = {
  thread_id: string;
  user_message_id: string;
  assistant_message_id: string;
  answer: string;
  citations: ChatCitation[];
  synced_document_count: number;
  available_document_count: number;
};

export type TrainingAttempt = {
  id: string;
  role: string;
  status: string;
  scenario: string;
  user_response: string | null;
  feedback: string | null;
  score: number | null;
  source_document_ids: string[];
  created_at: string;
  updated_at: string;
};

export type TrainingResult = {
  id: string;
  user_id: string | null;
  user_label: string;
  role: string;
  score: number | null;
  status: string;
  scenario_preview: string;
  created_at: string;
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
  timeoutMs?: number;
};

export async function getAuthSession(
  apiBaseUrl: string,
  getAccessToken: AuthTokenGetter
): Promise<AuthSession> {
  return apiRequest<AuthSession>(apiBaseUrl, "/auth/session", getAccessToken);
}

export async function createCompany(
  apiBaseUrl: string,
  getAccessToken: AuthTokenGetter,
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
  getAccessToken: AuthTokenGetter,
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

export async function getCompanyMemberships(
  apiBaseUrl: string,
  getAccessToken: AuthTokenGetter
): Promise<CompanyMembership[]> {
  return apiRequest<CompanyMembership[]>(
    apiBaseUrl,
    "/auth/company/memberships",
    getAccessToken
  );
}

export async function upsertCompanyMembership(
  apiBaseUrl: string,
  getAccessToken: AuthTokenGetter,
  input: UpsertCompanyMembershipInput
): Promise<CompanyMembership> {
  return apiRequest<CompanyMembership>(
    apiBaseUrl,
    "/auth/company/memberships",
    getAccessToken,
    {
      body: JSON.stringify(input),
      method: "POST"
    }
  );
}

export async function getDocuments(
  apiBaseUrl: string,
  getAccessToken: AuthTokenGetter
): Promise<DocumentRecord[]> {
  return apiRequest<DocumentRecord[]>(apiBaseUrl, "/documents", getAccessToken);
}

export async function uploadDocument(
  apiBaseUrl: string,
  getAccessToken: AuthTokenGetter,
  file: File,
  metadata: {
    allowedRoles?: CompanyRole[];
    locationLabel?: string | null;
    trainingEnabled?: boolean;
  } = {}
): Promise<DocumentRecord> {
  const payload = new FormData();
  payload.append("file", file);
  if (metadata.allowedRoles?.length) {
    payload.append("allowed_roles", JSON.stringify(metadata.allowedRoles));
  }
  if (metadata.locationLabel) {
    payload.append("location_label", metadata.locationLabel);
  }
  payload.append("training_enabled", metadata.trainingEnabled ? "true" : "false");

  return apiRequest<DocumentRecord>(apiBaseUrl, "/documents", getAccessToken, {
    body: payload,
    method: "POST"
  });
}

export async function askDocumentQuestion(
  apiBaseUrl: string,
  getAccessToken: AuthTokenGetter,
  question: string,
  threadId: string | null
): Promise<ChatAnswer> {
  return apiRequest<ChatAnswer>(
    apiBaseUrl,
    "/chat/messages",
    getAccessToken,
    {
      body: JSON.stringify({
        question,
        thread_id: threadId
      }),
      method: "POST",
      timeoutMs: 240000
    }
  );
}

export async function startTrainingScenario(
  apiBaseUrl: string,
  getAccessToken: AuthTokenGetter
): Promise<TrainingAttempt> {
  return apiRequest<TrainingAttempt>(
    apiBaseUrl,
    "/training/scenarios",
    getAccessToken,
    {
      method: "POST",
      timeoutMs: 240000
    }
  );
}

export async function submitTrainingAttempt(
  apiBaseUrl: string,
  getAccessToken: AuthTokenGetter,
  attemptId: string,
  userResponse: string
): Promise<TrainingAttempt> {
  return apiRequest<TrainingAttempt>(
    apiBaseUrl,
    `/training/attempts/${attemptId}/submit`,
    getAccessToken,
    {
      body: JSON.stringify({ user_response: userResponse }),
      method: "POST",
      timeoutMs: 240000
    }
  );
}

export async function getTrainingResults(
  apiBaseUrl: string,
  getAccessToken: AuthTokenGetter
): Promise<TrainingResult[]> {
  return apiRequest<TrainingResult[]>(
    apiBaseUrl,
    "/training/results",
    getAccessToken
  );
}

async function apiRequest<T>(
  apiBaseUrl: string,
  path: string,
  getAccessToken: AuthTokenGetter,
  init: ApiRequestInit = {}
): Promise<T> {
  const token = await getAccessToken();
  const headers = new Headers(init.headers);
  const controller = init.timeoutMs ? new AbortController() : undefined;
  const timeoutId = init.timeoutMs
    ? window.setTimeout(() => controller?.abort(), init.timeoutMs)
    : undefined;
  headers.set("Authorization", `Bearer ${token.accessToken}`);
  if (token.idToken) {
    headers.set("X-Auth0-ID-Token", token.idToken);
  }

  if (!(init.body instanceof FormData) && init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      cache: "no-store",
      headers,
      signal: controller?.signal
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The request timed out. Try again in a moment.", 408);
    }

    if (error instanceof TypeError) {
      throw new ApiError(
        `Unable to reach the API at ${apiBaseUrl}. Check that the API is running and that CORS allows this web address.`,
        0
      );
    }

    throw error;
  } finally {
    if (timeoutId) {
      window.clearTimeout(timeoutId);
    }
  }

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
