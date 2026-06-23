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
