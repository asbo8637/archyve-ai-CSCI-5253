"use client";

import { useAuth0 } from "@auth0/auth0-react";
import {
  ChangeEvent,
  Dispatch,
  FormEvent,
  SetStateAction,
  useEffect,
  useRef,
  useState
} from "react";

import {
  ApiError,
  createCompany,
  getAuthSession,
  getDocuments,
  selectCompany,
  uploadDocument,
  type AccessTokenGetter,
  type AuthSession
} from "@/lib/api";
import {
  getDocumentStatusLabel,
  type DocumentRecord,
  SUPPORTED_DOCUMENT_ACCEPT
} from "@/lib/documents";

type DashboardProps = {
  apiBaseUrl: string;
  authConfigured: boolean;
};

export function DocumentDashboard({
  apiBaseUrl,
  authConfigured
}: DashboardProps) {
  if (!authConfigured) {
    return (
      <div className="shell">
        <section className="hero">
          <span className="eyebrow">Auth Configuration Required</span>
          <h1>Set the Auth0 web environment before loading the app.</h1>
          <p>
            Configure `NEXT_PUBLIC_AUTH0_DOMAIN`, `NEXT_PUBLIC_AUTH0_CLIENT_ID`,
            and `NEXT_PUBLIC_AUTH0_AUDIENCE`, then reload this page.
          </p>
        </section>
      </div>
    );
  }

  return <AuthenticatedDocumentDashboard apiBaseUrl={apiBaseUrl} />;
}

function AuthenticatedDocumentDashboard({
  apiBaseUrl
}: {
  apiBaseUrl: string;
}) {
  const {
    error: authError,
    getAccessTokenSilently,
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout,
    user
  } = useAuth0();

  const [companyName, setCompanyName] = useState("");
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [session, setSession] = useState<AuthSession | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [submitState, setSubmitState] = useState<
    "idle" | "creating-company" | "switching-company" | "uploading"
  >("idle");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      setCompanyName("");
      setDocuments([]);
      setError(null);
      setMessage(null);
      setSelectedFile(null);
      setSession(null);
      return;
    }

    const accessTokenGetter = createAccessTokenGetter(getAccessTokenSilently);
    void loadWorkspace(
      apiBaseUrl,
      accessTokenGetter,
      setDocuments,
      setError,
      setSessionLoading,
      setSession
    );
  }, [apiBaseUrl, getAccessTokenSilently, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated || !session?.active_company) {
      return;
    }

    const accessTokenGetter = createAccessTokenGetter(getAccessTokenSilently);
    const interval = window.setInterval(() => {
      void refreshDocuments(apiBaseUrl, accessTokenGetter, setDocuments);
    }, 3000);

    return () => window.clearInterval(interval);
  }, [apiBaseUrl, getAccessTokenSilently, isAuthenticated, session?.active_company?.id]);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      setError("Pick a file before uploading.");
      return;
    }

    setSubmitState("uploading");
    setMessage(null);
    setError(null);

    try {
      const created = await uploadDocument(
        apiBaseUrl,
        createAccessTokenGetter(getAccessTokenSilently),
        selectedFile
      );
      setDocuments((current) => [created, ...current]);
      setSelectedFile(null);
      setMessage(`${created.filename} was uploaded and queued for processing.`);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (uploadError) {
      setError(toDisplayMessage(uploadError, "Upload failed."));
    } finally {
      setSubmitState("idle");
    }
  }

  async function handleCreateCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitState("creating-company");
    setMessage(null);
    setError(null);

    try {
      const nextSession = await createCompany(
        apiBaseUrl,
        createAccessTokenGetter(getAccessTokenSilently),
        companyName
      );
      setCompanyName("");
      await applySession(
        apiBaseUrl,
        createAccessTokenGetter(getAccessTokenSilently),
        nextSession,
        setDocuments,
        setSession
      );
      setMessage(`Created ${nextSession.active_company?.name ?? "your company"}.`);
    } catch (createError) {
      setError(toDisplayMessage(createError, "Unable to create company."));
    } finally {
      setSubmitState("idle");
    }
  }

  async function handleCompanySwitch(event: ChangeEvent<HTMLSelectElement>) {
    const nextCompanyId = event.target.value;
    if (!nextCompanyId) {
      return;
    }

    setSubmitState("switching-company");
    setMessage(null);
    setError(null);

    try {
      const nextSession = await selectCompany(
        apiBaseUrl,
        createAccessTokenGetter(getAccessTokenSilently),
        nextCompanyId
      );
      await applySession(
        apiBaseUrl,
        createAccessTokenGetter(getAccessTokenSilently),
        nextSession,
        setDocuments,
        setSession
      );
    } catch (switchError) {
      setError(toDisplayMessage(switchError, "Unable to switch companies."));
    } finally {
      setSubmitState("idle");
    }
  }

  return (
    <div className="shell">
      <section className="hero">
        <div className="hero-row">
          <div>
            <span className="eyebrow">Auth0 + Company Scope</span>
            <h1>Secure uploads and retrieval stay isolated to one company at a time.</h1>
          </div>
          {isAuthenticated ? (
            <button
              className="button button-secondary"
              onClick={() =>
                logout({
                  logoutParams: {
                    returnTo:
                      typeof window === "undefined" ? undefined : window.location.origin
                  }
                })
              }
              type="button"
            >
              Log Out
            </button>
          ) : null}
        </div>
        <p>
          The browser authenticates with Auth0, the API verifies every bearer
          token, and Postgres decides which company the request is allowed to
          act inside.
        </p>
        <div className="hero-actions">
          <span className="meta">
            {user?.name ?? user?.email ?? "Sign in to create or join a company."}
          </span>
          {authError ? null : isLoading ? (
            <span className="meta">Checking your Auth0 session...</span>
          ) : isAuthenticated ? (
            <span className="meta">
              {session?.memberships.length
                ? `Memberships loaded: ${session.memberships.length}`
                : "Authenticated. Finish company setup to continue."}
            </span>
          ) : (
            <div className="hero-button-group">
              <button
                className="button"
                onClick={() => void loginWithRedirect()}
                type="button"
              >
                Log In
              </button>
              <button
                className="button button-secondary"
                onClick={() =>
                  void loginWithRedirect({
                    authorizationParams: {
                      screen_hint: "signup"
                    }
                  })
                }
                type="button"
              >
                Sign Up
              </button>
            </div>
          )}
        </div>
      </section>

      {authError ? (
        <section className="panel notice">
          <h2>Authentication Error</h2>
          <p className="meta">{authError.message}</p>
        </section>
      ) : null}

      {!isAuthenticated ? null : sessionLoading ? (
        <section className="panel notice">
          <h2>Loading Workspace</h2>
          <p className="meta">Validating the session and resolving company access.</p>
        </section>
      ) : session?.needs_company_setup ? (
        <section className="panel stack">
          <h2>Create Your Company</h2>
          <p className="meta">
            This Auth0 user does not belong to a company yet. Create the first
            company to continue.
          </p>
          <form className="uploader" onSubmit={handleCreateCompany}>
            <input
              onChange={(event) => {
                setCompanyName(event.target.value);
                setError(null);
              }}
              placeholder="Company name"
              type="text"
              value={companyName}
            />
            <button className="button" disabled={submitState === "creating-company"}>
              {submitState === "creating-company" ? "Creating..." : "Create Company"}
            </button>
          </form>
          {error ? (
            <p className="meta error" role="alert">
              {error}
            </p>
          ) : null}
        </section>
      ) : (
        <section className="dashboard">
          <div className="panel stack">
            <div>
              <h2>{session?.active_company?.name ?? "Select a company"}</h2>
              <p className="meta">
                Active role: {session?.active_company?.role ?? "none"}
              </p>
            </div>

            {session?.memberships && session.memberships.length > 1 ? (
              <label className="stack" htmlFor="company-switcher">
                <span className="meta">Switch company</span>
                <select
                  className="company-select"
                  id="company-switcher"
                  onChange={handleCompanySwitch}
                  value={session.active_company?.id ?? ""}
                >
                  <option value="" disabled>
                    Select a company
                  </option>
                  {session.memberships.map((membership) => (
                    <option key={membership.company_id} value={membership.company_id}>
                      {membership.company_name} ({membership.role})
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            {session?.company_selection_required ? (
              <div className="callout">
                Choose a company membership before loading company-scoped data.
              </div>
            ) : (
              <>
                <form className="uploader" onSubmit={handleUpload}>
                  <input
                    id="file"
                    ref={fileInputRef}
                    type="file"
                    accept={SUPPORTED_DOCUMENT_ACCEPT}
                    onChange={(event) => {
                      setSelectedFile(event.target.files?.[0] ?? null);
                      setError(null);
                    }}
                  />
                  <button className="button" disabled={submitState === "uploading"}>
                    {submitState === "uploading" ? "Uploading..." : "Upload Document"}
                  </button>
                </form>
                {message ? <div className="callout">{message}</div> : null}
              </>
            )}

            {error ? (
              <p className="meta error" role="alert">
                {error}
              </p>
            ) : null}
          </div>

          <div className="panel">
            <div className="doc-row">
              <div>
                <h3>Documents</h3>
                <p className="meta">
                  The API lists and uploads documents only inside the active company.
                </p>
              </div>
              <span className="meta">{documents.length} total</span>
            </div>

            <div className="doc-list">
              {documents.length === 0 ? (
                <div className="doc-card">
                  <span className="doc-name">No documents for this company yet</span>
                  <span className="meta">
                    Start with a `.txt`, `.pdf`, `.docx`, `.csv`, or `.json` file.
                  </span>
                </div>
              ) : (
                documents.map((document) => (
                  <div className="doc-card" key={document.id}>
                    <div className="doc-row">
                      <span className="doc-name">{document.filename}</span>
                      <span className={`badge badge-${document.status}`}>
                        {getDocumentStatusLabel(document.status)}
                      </span>
                    </div>
                    <span className="meta">
                      Updated {new Date(document.updated_at).toLocaleString()}
                    </span>
                    {document.failure_reason ? (
                      <span className="meta error">{document.failure_reason}</span>
                    ) : null}
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

function createAccessTokenGetter(
  getAccessTokenSilently: ReturnType<typeof useAuth0>["getAccessTokenSilently"]
): AccessTokenGetter {
  return async () =>
    getAccessTokenSilently({
      authorizationParams: {
        scope: "openid profile email offline_access"
      }
    });
}

async function loadWorkspace(
  apiBaseUrl: string,
  getAccessToken: AccessTokenGetter,
  setDocuments: Dispatch<SetStateAction<DocumentRecord[]>>,
  setError: Dispatch<SetStateAction<string | null>>,
  setSessionLoading: Dispatch<SetStateAction<boolean>>,
  setSession: Dispatch<SetStateAction<AuthSession | null>>
) {
  setSessionLoading(true);
  setError(null);

  try {
    const nextSession = await getAuthSession(apiBaseUrl, getAccessToken);
    await applySession(apiBaseUrl, getAccessToken, nextSession, setDocuments, setSession);
  } catch (loadError) {
    setDocuments([]);
    setSession(null);
    setError(toDisplayMessage(loadError, "Unable to load the authenticated session."));
  } finally {
    setSessionLoading(false);
  }
}

async function applySession(
  apiBaseUrl: string,
  getAccessToken: AccessTokenGetter,
  nextSession: AuthSession,
  setDocuments: Dispatch<SetStateAction<DocumentRecord[]>>,
  setSession: Dispatch<SetStateAction<AuthSession | null>>
) {
  setSession(nextSession);

  if (!nextSession.active_company) {
    setDocuments([]);
    return;
  }

  const nextDocuments = await getDocuments(apiBaseUrl, getAccessToken);
  setDocuments(nextDocuments);
}

async function refreshDocuments(
  apiBaseUrl: string,
  getAccessToken: AccessTokenGetter,
  setDocuments: Dispatch<SetStateAction<DocumentRecord[]>>
) {
  try {
    const nextDocuments = await getDocuments(apiBaseUrl, getAccessToken);
    setDocuments(nextDocuments);
  } catch (refreshError) {
    if (
      refreshError instanceof ApiError &&
      [401, 403, 409].includes(refreshError.status)
    ) {
      return;
    }
  }
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
