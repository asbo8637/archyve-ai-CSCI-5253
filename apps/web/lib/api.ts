import type { DocumentRecord } from "@/lib/documents";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiRequest<T>(apiBaseUrl: string, path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new ApiError(body?.detail ?? "Request failed.", response.status);
  }
  return response.json() as Promise<T>;
}

export async function getDocuments(apiBaseUrl: string): Promise<DocumentRecord[]> {
  return apiRequest<DocumentRecord[]>(apiBaseUrl, "/documents");
}

export async function uploadDocument(apiBaseUrl: string, file: File): Promise<DocumentRecord> {
  const payload = new FormData();
  payload.append("file", file);
  return apiRequest<DocumentRecord>(apiBaseUrl, "/documents", { method: "POST", body: payload });
}
