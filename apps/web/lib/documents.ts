export const SUPPORTED_DOCUMENT_EXTENSIONS = [
  ".txt",
  ".md",
  ".pdf",
  ".docx",
  ".csv",
  ".json"
] as const;

export const SUPPORTED_DOCUMENT_ACCEPT = SUPPORTED_DOCUMENT_EXTENSIONS.join(",");

export type DocumentStatus = "processing" | "ready" | "failed";

export type DocumentRecord = {
  id: string;
  filename: string;
  status: DocumentStatus;
  failure_reason: string | null;
  updated_at: string;
};

const STATUS_LABELS: Record<DocumentStatus, string> = {
  processing: "Processing",
  ready: "Ready",
  failed: "Failed"
};

export function getDocumentStatusLabel(status: DocumentStatus): string {
  return STATUS_LABELS[status];
}

export const MOCK_DOCUMENTS: DocumentRecord[] = [
  {
    id: "1",
    filename: "q4-report.pdf",
    status: "ready",
    failure_reason: null,
    updated_at: new Date(Date.now() - 1000 * 60 * 5).toISOString()
  },
  {
    id: "2",
    filename: "onboarding-guide.docx",
    status: "processing",
    failure_reason: null,
    updated_at: new Date(Date.now() - 1000 * 30).toISOString()
  },
  {
    id: "3",
    filename: "corrupted-file.csv",
    status: "failed",
    failure_reason: "Could not parse file encoding.",
    updated_at: new Date(Date.now() - 1000 * 60 * 60).toISOString()
  }
];
