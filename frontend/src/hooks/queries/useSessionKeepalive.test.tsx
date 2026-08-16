import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { server } from "@/mocks/server";

import {
  SESSION_KEEPALIVE_INTERVAL_MS,
  useSessionKeepalive,
} from "./useSessionKeepalive";

function spyHandler(status = 200) {
  const calls = { count: 0 };
  server.use(
    http.post("/api/auth/extend", () => {
      calls.count += 1;
      if (status === 200) {
        return HttpResponse.json({ message: "Session extended" });
      }
      return HttpResponse.json({ detail: "Not authenticated" }, { status });
    }),
  );
  return calls;
}

describe("useSessionKeepalive", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("calls /auth/extend once on mount", async () => {
    const calls = spyHandler();

    renderHook(() => useSessionKeepalive());

    await waitFor(() => expect(calls.count).toBe(1));
  });

  it("calls /auth/extend again every 60 seconds", async () => {
    const calls = spyHandler();

    renderHook(() => useSessionKeepalive());

    await waitFor(() => expect(calls.count).toBe(1));

    await act(async () => {
      vi.advanceTimersByTime(SESSION_KEEPALIVE_INTERVAL_MS);
    });
    await waitFor(() => expect(calls.count).toBe(2));

    await act(async () => {
      vi.advanceTimersByTime(SESSION_KEEPALIVE_INTERVAL_MS);
    });
    await waitFor(() => expect(calls.count).toBe(3));
  });

  it("stops calling /auth/extend after unmount", async () => {
    const calls = spyHandler();

    const { unmount } = renderHook(() => useSessionKeepalive());
    await waitFor(() => expect(calls.count).toBe(1));

    unmount();

    await act(async () => {
      vi.advanceTimersByTime(SESSION_KEEPALIVE_INTERVAL_MS * 3);
    });

    expect(calls.count).toBe(1);
  });

  it("swallows a 401 without throwing", async () => {
    const calls = spyHandler(401);
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    renderHook(() => useSessionKeepalive());

    await waitFor(() => expect(calls.count).toBe(1));
    expect(errorSpy).not.toHaveBeenCalled();

    errorSpy.mockRestore();
  });
});
