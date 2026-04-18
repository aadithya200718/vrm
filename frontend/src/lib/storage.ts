import { APPROVAL_TOKEN_STORAGE_KEY } from "./config";

export function getStoredApprovalToken() {
  if (typeof window === "undefined") {
    return "";
  }

  return window.localStorage.getItem(APPROVAL_TOKEN_STORAGE_KEY) || "";
}

export function setStoredApprovalToken(value: string) {
  if (typeof window === "undefined") {
    return;
  }

  const normalized = value.trim();
  if (!normalized) {
    window.localStorage.removeItem(APPROVAL_TOKEN_STORAGE_KEY);
    return;
  }

  window.localStorage.setItem(APPROVAL_TOKEN_STORAGE_KEY, normalized);
}
