function normalizeApiBaseUrl(rawValue: string | undefined) {
  const trimmed = (rawValue?.trim() || "http://127.0.0.1:8000").replace(
    /\/$/,
    "",
  );
  return trimmed.endsWith("/api/v1") ? trimmed : `${trimmed}/api/v1`;
}

export const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL,
);
export const ENV_APPROVAL_TOKEN =
  import.meta.env.VITE_APPROVER_BEARER_TOKEN?.trim() || "";
export const APPROVAL_TOKEN_STORAGE_KEY = "hackstrom.approval-token";
