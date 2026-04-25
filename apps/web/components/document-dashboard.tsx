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
  getCompanyMemberships,
  getAuthSession,
  getDocuments,
  selectCompany,
  upsertCompanyMembership,
  uploadDocument,
  type AccessTokenGetter,
  type AuthSession,
  type CompanyMembership,
  type CompanyRole
} from "@/lib/api";
import { CompanyChat } from "@/components/company-chat";
import { TrainingPanel } from "@/components/training-panel";
import {
  getDocumentStatusLabel,
  type DocumentRecord,
  SUPPORTED_DOCUMENT_ACCEPT
} from "@/lib/documents";

type DashboardProps = {
  apiBaseUrl: string;
  authConfigured: boolean;
};

const COMPANY_ROLE_OPTIONS: Array<{ value: CompanyRole; label: string }> = [
  { value: "admin", label: "Admin" },
  { value: "manager", label: "Manager" },
  { value: "employee", label: "Employee" },
  { value: "trainee", label: "Trainee" }
];

const FALLBACK_DOCUMENT_ROLES: CompanyRole[] = ["admin"];

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
    getIdTokenClaims,
    getAccessTokenSilently,
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout,
    user
  } = useAuth0();

  const [companyName, setCompanyName] = useState("");
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [companyMemberships, setCompanyMemberships] = useState<CompanyMembership[]>([]);
  const [documentAllowedRoles, setDocumentAllowedRoles] =
    useState<CompanyRole[]>(FALLBACK_DOCUMENT_ROLES);
  const [documentTrainingEnabled, setDocumentTrainingEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [memberEmail, setMemberEmail] = useState("");
  const [memberRole, setMemberRole] = useState<CompanyRole>("employee");
  const [message, setMessage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [session, setSession] = useState<AuthSession | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [submitState, setSubmitState] = useState<
    "idle" | "creating-company" | "switching-company" | "uploading" | "saving-member"
  >("idle");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const canManageMemberships = Boolean(session?.permissions.includes("memberships:manage"));
  const canUploadDocuments = Boolean(session?.permissions.includes("documents:write"));

  useEffect(() => {
    if (!isAuthenticated) {
      setCompanyName("");
      setCompanyMemberships([]);
      setDocuments([]);
      setDocumentAllowedRoles(FALLBACK_DOCUMENT_ROLES);
      setDocumentTrainingEnabled(false);
      setError(null);
      setMemberEmail("");
      setMemberRole("employee");
      setMessage(null);
      setSelectedFile(null);
      setSession(null);
      return;
    }

    const accessTokenGetter = createAccessTokenGetter(
      getAccessTokenSilently,
      getIdTokenClaims
    );
    void loadWorkspace(
      apiBaseUrl,
      accessTokenGetter,
      setDocuments,
      setError,
      setSessionLoading,
      setSession
    );
  }, [apiBaseUrl, getAccessTokenSilently, getIdTokenClaims, isAuthenticated]);

  useEffect(() => {
    setDocumentAllowedRoles(
      defaultDocumentRolesForRole(session?.active_company?.role ?? null)
    );
    setDocumentTrainingEnabled(false);
  }, [session?.active_company?.id, session?.active_company?.role]);

  useEffect(() => {
    if (!isAuthenticated || !session?.active_company) {
      return;
    }

    const accessTokenGetter = createAccessTokenGetter(
      getAccessTokenSilently,
      getIdTokenClaims
    );
    const interval = window.setInterval(() => {
      void refreshDocuments(apiBaseUrl, accessTokenGetter, setDocuments);
    }, 3000);

    return () => window.clearInterval(interval);
  }, [
    apiBaseUrl,
    getAccessTokenSilently,
    getIdTokenClaims,
    isAuthenticated,
    session?.active_company?.id
  ]);

  useEffect(() => {
    if (!isAuthenticated || !session?.active_company || !canManageMemberships) {
      setCompanyMemberships([]);
      return;
    }

    const accessTokenGetter = createAccessTokenGetter(
      getAccessTokenSilently,
      getIdTokenClaims
    );
    void refreshCompanyMemberships(
      apiBaseUrl,
      accessTokenGetter,
      setCompanyMemberships,
      setError
    );
  }, [
    apiBaseUrl,
    canManageMemberships,
    getAccessTokenSilently,
    getIdTokenClaims,
    isAuthenticated,
    session?.active_company?.id
  ]);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      setError("Pick a file before uploading.");
      return;
    }

    if (!canUploadDocuments) {
      setError("Your role cannot upload company documents.");
      return;
    }

    setSubmitState("uploading");
    setMessage(null);
    setError(null);

    try {
      const created = await uploadDocument(
        apiBaseUrl,
        createAccessTokenGetter(getAccessTokenSilently, getIdTokenClaims),
        selectedFile,
        {
          allowedRoles: documentAllowedRoles,
          trainingEnabled: documentTrainingEnabled
        }
      );
      setDocuments((current) => [created, ...current]);
      setSelectedFile(null);
      setDocumentAllowedRoles(
        defaultDocumentRolesForRole(session?.active_company?.role ?? null)
      );
      setDocumentTrainingEnabled(false);
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
        createAccessTokenGetter(getAccessTokenSilently, getIdTokenClaims),
        companyName
      );
      setCompanyName("");
      await applySession(
        apiBaseUrl,
        createAccessTokenGetter(getAccessTokenSilently, getIdTokenClaims),
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

  async function handleMemberSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!canManageMemberships) {
      setError("Your role cannot manage company memberships.");
      return;
    }

    setSubmitState("saving-member");
    setMessage(null);
    setError(null);

    try {
      const saved = await upsertCompanyMembership(
        apiBaseUrl,
        createAccessTokenGetter(getAccessTokenSilently, getIdTokenClaims),
        {
          email: memberEmail,
          role: memberRole
        }
      );
      setCompanyMemberships((current) => [
        saved,
        ...current.filter((membership) => membership.id !== saved.id)
      ]);
      setMemberEmail("");
      setMemberRole("employee");
      setMessage(`Saved ${saved.email ?? "member"} as ${saved.role}.`);
    } catch (membershipError) {
      setError(toDisplayMessage(membershipError, "Unable to save membership."));
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
        createAccessTokenGetter(getAccessTokenSilently, getIdTokenClaims),
        nextCompanyId
      );
      await applySession(
        apiBaseUrl,
        createAccessTokenGetter(getAccessTokenSilently, getIdTokenClaims),
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

  function handleRetryWorkspace() {
    const accessTokenGetter = createAccessTokenGetter(getAccessTokenSilently, getIdTokenClaims);
    void loadWorkspace(
      apiBaseUrl,
      accessTokenGetter,
      setDocuments,
      setError,
      setSessionLoading,
      setSession
    );
  }

  function toggleDocumentRole(role: CompanyRole, checked: boolean) {
    setDocumentAllowedRoles((current) => {
      if (checked) {
        return Array.from(new Set([...current, role]));
      }

      const nextRoles = current.filter((candidate) => candidate !== role);
      return nextRoles.length ? nextRoles : ["admin"];
    });
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
      ) : !session ? (
        <section className="panel notice">
          <h2>Unable to Load Workspace</h2>
          <p className="meta">
            The app could not reach the API session endpoint. Company setup will
            appear after the session loads.
          </p>
          {error ? (
            <p className="meta error" role="alert">
              {error}
            </p>
          ) : null}
          <button className="button" onClick={handleRetryWorkspace} type="button">
            Retry
          </button>
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
                {canUploadDocuments ? (
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
                    <div className="role-picker" aria-label="Document visibility">
                      {COMPANY_ROLE_OPTIONS.map((role) => (
                        <label key={role.value}>
                          <input
                            checked={documentAllowedRoles.includes(role.value)}
                            onChange={(event) =>
                              toggleDocumentRole(role.value, event.target.checked)
                            }
                            type="checkbox"
                          />
                          <span>{role.label}</span>
                        </label>
                      ))}
                    </div>
                    <label className="training-toggle">
                      <input
                        checked={documentTrainingEnabled}
                        onChange={(event) =>
                          setDocumentTrainingEnabled(event.target.checked)
                        }
                        type="checkbox"
                      />
                      <span>Use for training scenarios</span>
                    </label>
                    <button className="button" disabled={submitState === "uploading"}>
                      {submitState === "uploading" ? "Uploading..." : "Upload Document"}
                    </button>
                  </form>
                ) : (
                  <p className="meta">Your role can ask questions but cannot upload documents.</p>
                )}
                {message ? <div className="callout">{message}</div> : null}
              </>
            )}

            {error ? (
              <p className="meta error" role="alert">
                {error}
              </p>
            ) : null}

            {canManageMemberships ? (
              <div className="membership-panel">
                <div>
                  <h3>Members</h3>
                  <p className="meta">
                    Add existing or future users by email and assign their company role.
                  </p>
                </div>
                <form className="uploader" onSubmit={handleMemberSave}>
                  <input
                    onChange={(event) => setMemberEmail(event.target.value)}
                    placeholder="email@example.com"
                    type="email"
                    value={memberEmail}
                  />
                  <select
                    className="company-select"
                    onChange={(event) => setMemberRole(event.target.value as CompanyRole)}
                    value={memberRole}
                  >
                    {COMPANY_ROLE_OPTIONS.map((role) => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                  <button className="button" disabled={submitState === "saving-member"}>
                    {submitState === "saving-member" ? "Saving..." : "Save Member"}
                  </button>
                </form>
                <div className="membership-list">
                  {companyMemberships.map((membership) => (
                    <div className="membership-row" key={membership.id}>
                      <div>
                        <span className="doc-name">
                          {membership.email ?? "Member"}
                        </span>
                      </div>
                      <span className="badge">{membership.role}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>

          <div className="stack">
            <TrainingPanel
              apiBaseUrl={apiBaseUrl}
              canViewResults={
                session?.active_company?.role === "admin" ||
                session?.active_company?.role === "manager"
              }
              disabled={
                Boolean(session?.company_selection_required) ||
                !session?.active_company
              }
              getAccessToken={createAccessTokenGetter(getAccessTokenSilently, getIdTokenClaims)}
            />

            <CompanyChat
              apiBaseUrl={apiBaseUrl}
              disabled={
                Boolean(session?.company_selection_required) ||
                !session?.active_company
              }
              getAccessToken={createAccessTokenGetter(getAccessTokenSilently, getIdTokenClaims)}
            />

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
                      <span className="meta">
                        Roles: {document.allowed_roles.join(", ")}
                        {document.training_enabled ? " · Training enabled" : ""}
                      </span>
                      {document.failure_reason ? (
                        <span className="meta error">{document.failure_reason}</span>
                      ) : null}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

function createAccessTokenGetter(
  getAccessTokenSilently: ReturnType<typeof useAuth0>["getAccessTokenSilently"],
  getIdTokenClaims: ReturnType<typeof useAuth0>["getIdTokenClaims"]
): AccessTokenGetter {
  return async () => {
    const [accessToken, idTokenClaims] = await Promise.all([
      getAccessTokenSilently({
        authorizationParams: {
          scope: "openid profile email offline_access"
        }
      }),
      getIdTokenClaims()
    ]);

    return {
      accessToken,
      idToken: idTokenClaims?.__raw
    };
  };
}

function defaultDocumentRolesForRole(role: string | null): CompanyRole[] {
  if (isCompanyRole(role)) {
    return [role];
  }

  return FALLBACK_DOCUMENT_ROLES;
}

function isCompanyRole(role: string | null): role is CompanyRole {
  return COMPANY_ROLE_OPTIONS.some((option) => option.value === role);
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

async function refreshCompanyMemberships(
  apiBaseUrl: string,
  getAccessToken: AccessTokenGetter,
  setCompanyMemberships: Dispatch<SetStateAction<CompanyMembership[]>>,
  setError: Dispatch<SetStateAction<string | null>>
) {
  try {
    const memberships = await getCompanyMemberships(apiBaseUrl, getAccessToken);
    setCompanyMemberships(memberships);
  } catch (membershipError) {
    setError(toDisplayMessage(membershipError, "Unable to load company members."));
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
