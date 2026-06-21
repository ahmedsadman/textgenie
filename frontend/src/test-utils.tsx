import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";
import { BrowserRouter, Outlet, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

export const mockUser = {
  id: 1,
  name: "Test User",
  email: "test@example.com",
  created_at: "2026-01-01T00:00:00Z",
};

export function mockFetch(status: number, body: unknown) {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response);
}

export function mockFetchSequence(
  ...responses: Array<{ status: number; body: unknown }>
) {
  const spy = vi.spyOn(globalThis, "fetch");
  for (const { status, body } of responses) {
    spy.mockResolvedValueOnce({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    } as Response);
  }
  return spy;
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <BrowserRouter>
      {children}
      <Toaster />
    </BrowserRouter>
  );
}

export function renderWithRouter(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return render(ui, { wrapper: Wrapper, ...options });
}

export function renderWithOutletContext<T extends Record<string, unknown>>(
  ui: ReactElement,
  context: T,
  options?: Omit<RenderOptions, "wrapper">,
) {
  function ContextWrapper({ children }: { children: React.ReactNode }) {
    return (
      <BrowserRouter>
        <Routes>
          <Route element={<Outlet context={context} />}>
            <Route index element={ui} />
          </Route>
        </Routes>
        <Toaster />
        {children}
      </BrowserRouter>
    );
  }

  return render(<></>, { wrapper: ContextWrapper, ...options });
}
