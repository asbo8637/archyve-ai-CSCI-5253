"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, getDocuments, uploadDocument } from "@/lib/api";
import {
  getDocumentStatusLabel,
  SUPPORTED_DOCUMENT_ACCEPT,
  type DocumentRecord
} from "@/lib/documents";

export function DocumentDashboard({ apiBaseUrl }: { apiBaseUrl: string }) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void load();
    const interval = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(interval);
  }, [apiBaseUrl]);

  async function load() {
    try {
      setDocuments(await getDocuments(apiBaseUrl));
    } catch {
      // silently skip on poll errors
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setMessage(null);
    setError(null);

    try {
      const created = await uploadDocument(apiBaseUrl, selectedFile);
      setDocuments((current) => [created, ...current]);
      setMessage(`${created.filename} was uploaded and queued for processing.`);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="shell">
      <section className="hero">
        <span className="eyebrow">Document Ingestion</span>
        <h1>Upload and index your documents.</h1>
        <p>Files are saved locally and queued for processing.</p>
      </section>

      <section className="dashboard">
        <div className="panel stack">
          <h2>Upload a Document</h2>
          <form className="uploader" onSubmit={handleUpload}>
            <input
              id="file"
              ref={fileInputRef}
              type="file"
              accept={SUPPORTED_DOCUMENT_ACCEPT}
              onChange={(e) => {
                setSelectedFile(e.target.files?.[0] ?? null);
                setError(null);
              }}
            />
            <button className="button" disabled={!selectedFile || uploading}>
              {uploading ? "Uploading..." : "Upload Document"}
            </button>
          </form>
          {message ? <div className="callout">{message}</div> : null}
          {error ? <p className="meta error">{error}</p> : null}
        </div>

        <div className="panel">
          <div className="doc-row">
            <h3>Documents</h3>
            <span className="meta">{documents.length} total</span>
          </div>

          <div className="doc-list">
            {documents.length === 0 ? (
              <div className="doc-card">
                <span className="doc-name">No documents yet</span>
                <span className="meta">Upload a file to get started.</span>
              </div>
            ) : (
              documents.map((doc) => (
                <div className="doc-card" key={doc.id}>
                  <div className="doc-row">
                    <span className="doc-name">{doc.filename}</span>
                    <span className={`badge badge-${doc.status}`}>
                      {getDocumentStatusLabel(doc.status)}
                    </span>
                  </div>
                  <span className="meta">
                    Updated {new Date(doc.updated_at).toLocaleString()}
                  </span>
                  {doc.failure_reason ? (
                    <span className="meta error">{doc.failure_reason}</span>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
