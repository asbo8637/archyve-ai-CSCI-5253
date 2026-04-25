"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ApiError,
  getTrainingResults,
  startTrainingScenario,
  submitTrainingAttempt,
  type AccessTokenGetter,
  type TrainingAttempt,
  type TrainingResult
} from "@/lib/api";

type TrainingPanelProps = {
  apiBaseUrl: string;
  canViewResults: boolean;
  disabled: boolean;
  getAccessToken: AccessTokenGetter;
};

export function TrainingPanel({
  apiBaseUrl,
  canViewResults,
  disabled,
  getAccessToken
}: TrainingPanelProps) {
  const [attempt, setAttempt] = useState<TrainingAttempt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingResults, setLoadingResults] = useState(false);
  const [results, setResults] = useState<TrainingResult[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [starting, setStarting] = useState(false);
  const [userResponse, setUserResponse] = useState("");

  useEffect(() => {
    if (!canViewResults || disabled) {
      setResults([]);
      return;
    }

    void refreshResults();
  }, [apiBaseUrl, canViewResults, disabled]);

  async function handleStart() {
    setAttempt(null);
    setError(null);
    setStarting(true);
    setUserResponse("");

    try {
      const nextAttempt = await startTrainingScenario(apiBaseUrl, getAccessToken);
      setAttempt(nextAttempt);
    } catch (startError) {
      setError(toDisplayMessage(startError, "Unable to start training."));
    } finally {
      setStarting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedResponse = userResponse.trim();
    if (!attempt || !trimmedResponse) {
      setError("Enter a response before submitting.");
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      const submittedAttempt = await submitTrainingAttempt(
        apiBaseUrl,
        getAccessToken,
        attempt.id,
        trimmedResponse
      );
      setAttempt(submittedAttempt);
      setUserResponse(submittedAttempt.user_response ?? trimmedResponse);
      if (canViewResults) {
        void refreshResults();
      }
    } catch (submitError) {
      setError(toDisplayMessage(submitError, "Unable to submit training."));
    } finally {
      setSubmitting(false);
    }
  }

  async function refreshResults() {
    setLoadingResults(true);

    try {
      const nextResults = await getTrainingResults(apiBaseUrl, getAccessToken);
      setResults(nextResults);
    } catch (resultsError) {
      setError(toDisplayMessage(resultsError, "Unable to load training results."));
    } finally {
      setLoadingResults(false);
    }
  }

  const submitted = attempt?.status === "submitted";

  return (
    <section className="panel training-panel">
      <div className="doc-row">
        <div>
          <h3>Training</h3>
          <p className="meta">Scenarios use documents visible to your role.</p>
        </div>
        {attempt?.score !== null && attempt?.score !== undefined ? (
          <span className="badge badge-ready">{attempt.score}/100</span>
        ) : null}
      </div>

      <button
        className="button button-secondary"
        disabled={disabled || starting || submitting}
        onClick={() => void handleStart()}
        type="button"
      >
        {starting ? "Starting..." : "Start Training"}
      </button>

      {attempt ? (
        <form className="training-form" onSubmit={handleSubmit}>
          <div className="training-scenario">
            <span className="doc-name">Scenario</span>
            <p>{attempt.scenario}</p>
          </div>

          <textarea
            disabled={disabled || submitting || submitted}
            onChange={(event) => {
              setUserResponse(event.target.value);
              setError(null);
            }}
            placeholder="Write your response"
            rows={5}
            value={userResponse}
          />

          <button
            className="button"
            disabled={disabled || submitting || submitted}
          >
            {submitting ? "Submitting..." : "Submit Response"}
          </button>
        </form>
      ) : null}

      {attempt?.feedback ? (
        <div className="training-result">
          <span className="doc-name">Feedback</span>
          <p>{attempt.feedback}</p>
        </div>
      ) : null}

      {error ? (
        <p className="meta error" role="alert">
          {error}
        </p>
      ) : null}

      {canViewResults ? (
        <div className="training-results">
          <div className="doc-row">
            <span className="doc-name">Results</span>
            <button
              className="button button-secondary button-small"
              disabled={disabled || loadingResults}
              onClick={() => void refreshResults()}
              type="button"
            >
              {loadingResults ? "Loading..." : "Refresh"}
            </button>
          </div>

          {results.length === 0 ? (
            <span className="meta">No training attempts yet.</span>
          ) : (
            results.map((result) => (
              <div className="training-result-row" key={result.id}>
                <div className="doc-row">
                  <span className="doc-name">{result.user_label}</span>
                  <span className="badge">
                    {result.score === null ? "No score" : `${result.score}/100`}
                  </span>
                </div>
                <span className="meta">
                  {result.role} · {result.status} ·{" "}
                  {new Date(result.created_at).toLocaleString()}
                </span>
                <span>{result.scenario_preview}</span>
              </div>
            ))
          )}
        </div>
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
