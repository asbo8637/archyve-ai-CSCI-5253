export const SUPPORTED_DOCUMENT_EXTENSIONS = [
  ".txt",
  ".md",
  ".pdf",
  ".docx",
  ".csv",
  ".json"
] as const;

export const SUPPORTED_DOCUMENT_ACCEPT = SUPPORTED_DOCUMENT_EXTENSIONS.join(",");

export type DocumentStatus =
  | "pending_upload"
  | "uploaded"
  | "processing"
  | "ready"
  | "failed";

export type DocumentRecord = {
  id: string;
  filename: string;
  status: DocumentStatus;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
};

const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, string> = {
  pending_upload: "Pending Upload",
  uploaded: "Uploaded",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed"
};

export function getDocumentStatusLabel(status: DocumentStatus): string {
  return DOCUMENT_STATUS_LABELS[status];
}
