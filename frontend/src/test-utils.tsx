import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
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

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        gcTime: 0,
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  });
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

export function renderWithQueryClient(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  const client = createTestQueryClient();
  function QueryWrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <BrowserRouter>
          {children}
          <Toaster />
        </BrowserRouter>
      </QueryClientProvider>
    );
  }
  return render(ui, { wrapper: QueryWrapper, ...options });
}

export function renderWithQueryClientAndOutletContext<
  T extends Record<string, unknown>,
>(ui: ReactElement, context: T, options?: Omit<RenderOptions, "wrapper">) {
  const client = createTestQueryClient();
  function QueryContextWrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <BrowserRouter>
          <Routes>
            <Route element={<Outlet context={context} />}>
              <Route index element={ui} />
            </Route>
          </Routes>
          <Toaster />
          {children}
        </BrowserRouter>
      </QueryClientProvider>
    );
  }
  return render(<></>, { wrapper: QueryContextWrapper, ...options });
}
