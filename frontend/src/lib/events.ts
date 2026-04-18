import { startTransition, useEffect, useState } from "react";
import { getVendorEventsUrl } from "./api";
import type { WorkflowEvent } from "./types";

type StreamMode = "idle" | "streaming" | "polling";

export function useVendorEventStream(vendorId?: string) {
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [mode, setMode] = useState<StreamMode>("idle");

  useEffect(() => {
    setEvents([]);

    if (!vendorId) {
      setMode("idle");
      return;
    }

    if (typeof window === "undefined" || typeof window.EventSource !== "function") {
      setMode("polling");
      return;
    }

    let cancelled = false;
    const source = new window.EventSource(getVendorEventsUrl(vendorId));

    source.onopen = () => {
      if (!cancelled) {
        setMode("streaming");
      }
    };

    source.onmessage = (message) => {
      try {
        const parsed = JSON.parse(message.data) as WorkflowEvent;
        startTransition(() => {
          setEvents((current) => [...current.slice(-79), parsed]);
        });
      } catch {
        // Ignore malformed frames.
      }
    };

    source.onerror = () => {
      if (!cancelled) {
        setMode("polling");
        source.close();
      }
    };

    return () => {
      cancelled = true;
      source.close();
    };
  }, [vendorId]);

  return { events, mode };
}
