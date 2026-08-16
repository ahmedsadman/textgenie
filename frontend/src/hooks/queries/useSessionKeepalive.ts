import { useEffect } from "react";

import { api } from "@/lib/api";

export const SESSION_KEEPALIVE_INTERVAL_MS = 60_000;

export function useSessionKeepalive(): void {
  useEffect(() => {
    const ping = () => {
      api.extend().catch(() => {});
    };

    ping();
    const id = window.setInterval(ping, SESSION_KEEPALIVE_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, []);
}
