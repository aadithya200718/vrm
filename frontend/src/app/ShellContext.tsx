import {
  createContext,
  startTransition,
  useEffect,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ENV_APPROVAL_TOKEN } from "../lib/config";
import { getVendorEventsUrl } from "../lib/api";
import {
  getStoredApprovalToken,
  setStoredApprovalToken,
} from "../lib/storage";
import type { WorkflowEvent } from "../lib/types";

type PanelName = "notifications" | "settings" | "support" | null;

type ShellContextValue = {
  searchValue: string;
  setSearchValue: (value: string) => void;
  activePanel: PanelName;
  openPanel: (panel: Exclude<PanelName, null>) => void;
  closePanel: () => void;
  approvalToken: string;
  setApprovalToken: (value: string) => void;
  activeVendorId: string;
  setActiveVendorId: (value: string) => void;
  liveEvents: WorkflowEvent[];
  eventMode: "idle" | "streaming" | "polling";
};

const ShellContext = createContext<ShellContextValue | null>(null);

export function ShellProvider({ children }: { children: ReactNode }) {
  const [searchValue, setSearchValueState] = useState("");
  const [activePanel, setActivePanel] = useState<PanelName>(null);
  const [approvalToken, setApprovalTokenState] = useState(
    () => getStoredApprovalToken() || ENV_APPROVAL_TOKEN || "",
  );
  const [activeVendorId, setActiveVendorIdState] = useState("");
  const [liveEvents, setLiveEvents] = useState<WorkflowEvent[]>([]);
  const [eventMode, setEventMode] = useState<"idle" | "streaming" | "polling">("idle");

  useEffect(() => {
    setLiveEvents([]);
    if (!activeVendorId) {
      setEventMode("idle");
      return;
    }
    if (typeof window === "undefined" || typeof window.EventSource !== "function") {
      setEventMode("polling");
      return;
    }

    let cancelled = false;
    const source = new window.EventSource(getVendorEventsUrl(activeVendorId));
    source.onopen = () => {
      if (!cancelled) {
        setEventMode("streaming");
      }
    };
    source.onmessage = (message) => {
      try {
        const parsed = JSON.parse(message.data) as WorkflowEvent;
        startTransition(() => {
          setLiveEvents((current) => [...current.slice(-79), parsed]);
        });
      } catch {
        // Ignore malformed frames.
      }
    };
    source.onerror = () => {
      if (!cancelled) {
        setEventMode("polling");
        source.close();
      }
    };
    return () => {
      cancelled = true;
      source.close();
    };
  }, [activeVendorId]);

  const value = useMemo<ShellContextValue>(
    () => ({
      searchValue,
      setSearchValue: (next) => {
        startTransition(() => setSearchValueState(next));
      },
      activePanel,
      openPanel: (panel) => setActivePanel(panel),
      closePanel: () => setActivePanel(null),
      approvalToken,
      setApprovalToken: (next) => {
        setApprovalTokenState(next);
        setStoredApprovalToken(next);
      },
      activeVendorId,
      setActiveVendorId: (next) => setActiveVendorIdState(next),
      liveEvents,
      eventMode,
    }),
    [activePanel, activeVendorId, approvalToken, eventMode, liveEvents, searchValue],
  );

  return (
    <ShellContext.Provider value={value}>{children}</ShellContext.Provider>
  );
}

export function useShell() {
  const value = useContext(ShellContext);
  if (!value) {
    throw new Error("useShell must be used inside ShellProvider");
  }
  return value;
}
