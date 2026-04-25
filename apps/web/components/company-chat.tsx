"use client";

import { FormEvent, useState } from "react";

import {
  ApiError,
  askDocumentQuestion,
  type AccessTokenGetter,
  type ChatCitation
} from "@/lib/api";

type CompanyChatProps = {
  apiBaseUrl: string;
  disabled: boolean;
  getAccessToken: AccessTokenGetter;
};

type ChatEntry = {
  id: string;
  role: "assistant" | "user";
  content: string;
  citations?: ChatCitation[];
};

export function CompanyChat({
  apiBaseUrl,
  disabled,
  getAccessToken
}: CompanyChatProps) {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      setError("Enter a question first.");
      return;
    }

    const pendingUserEntry: ChatEntry = {
      id: `pending-${Date.now()}`,
      role: "user",
      content: trimmedQuestion
    };

    setEntries((current) => [...current, pendingUserEntry]);
    setQuestion("");
    setSubmitting(true);
    setError(null);

    try {
      const response = await askDocumentQuestion(
        apiBaseUrl,
        getAccessToken,
        trimmedQuestion,
        threadId
      );
      setThreadId(response.thread_id);
      setEntries((current) => [
        ...current,
        {
          id: response.assistant_message_id,
          role: "assistant",
          content: response.answer,
          citations: response.citations
        }
      ]);
    } catch (chatError) {
      setError(toDisplayMessage(chatError, "Unable to answer that question."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel chat-panel">
      <div className="doc-row">
        <div>
          <h3>Ask Documents</h3>
          <p className="meta">Answers use the active company&apos;s ready documents.</p>
        </div>
        {threadId ? <span className="meta">Thread active</span> : null}
      </div>

      <div className="chat-log" aria-live="polite">
        {entries.length === 0 ? (
          <div className="chat-empty">
            <span className="doc-name">No questions yet</span>
            <span className="meta">Ask about a processed document.</span>
          </div>
        ) : (
          entries.map((entry) => (
            <article className={`chat-message chat-message-${entry.role}`} key={entry.id}>
              <p>{entry.content}</p>
              {entry.citations?.length ? (
                <div className="citation-list">
                  {entry.citations.map((citation, index) => (
                    <span
                      className="citation-pill"
                      key={`${entry.id}-${citation.document_name ?? index}`}
                      title={citation.text ?? citation.source_label}
                    >
                      {citation.source_label}
                    </span>
                  ))}
                </div>
              ) : null}
            </article>
          ))
        )}
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <textarea
          disabled={disabled || submitting}
          onChange={(event) => {
            setQuestion(event.target.value);
            setError(null);
          }}
          placeholder="Ask a question about your documents"
          rows={3}
          value={question}
        />
        <button className="button" disabled={disabled || submitting}>
          {submitting ? "Asking..." : "Send"}
        </button>
      </form>

      {error ? (
        <p className="meta error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}

function toDisplayMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}
