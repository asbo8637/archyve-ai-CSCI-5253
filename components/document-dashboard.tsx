"use client";

import { FormEvent, useRef, useState } from "react";
import {
  getDocumentStatusLabel,
  MOCK_DOCUMENTS,
  SUPPORTED_DOCUMENT_ACCEPT,
  type DocumentRecord
} from "@/lib/documents";

export function DocumentDashboard() {
  const [documents, setDocuments] = useState<DocumentRecord[]>(MOCK_DOCUMENTS);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setMessage(null);

    setTimeout(() => {
      const newDoc: DocumentRecord = {
        id: String(Date.now()),
        filename: selectedFile.name,
        status: "processing",
        failure_reason: null,
        updated_at: new Date().toISOString()
      };
      setDocuments((current) => [newDoc, ...current]);
      setMessage(`${selectedFile.name} was queued for processing.`);
      setSelectedFile(null);
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }, 600);
  }

  return (
    <div className="shell">
      <section className="hero">
        <span className="eyebrow">Document Ingestion</span>
        <h1>Upload and index your documents.</h1>
        <p>
          Upload files to Archyve AI. Supported formats: txt, md, pdf, docx,
          csv, json.
        </p>
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
                setMessage(null);
              }}
            />
            <button className="button" disabled={!selectedFile || uploading}>
              {uploading ? "Uploading..." : "Upload Document"}
            </button>
          </form>
          {message ? <div className="callout">{message}</div> : null}
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
