import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "@/mocks/server";
import RegisterPage from "@/pages/RegisterPage";
import { renderWithRouter } from "@/test-utils";

describe("RegisterPage", () => {
  it("renders all form fields", () => {
    renderWithRouter(<RegisterPage />);
    expect(screen.getByLabelText(/^name$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /create account/i }),
    ).toBeInTheDocument();
  });

  it("renders link to login page", () => {
    renderWithRouter(<RegisterPage />);
    const link = screen.getByRole("link", { name: /sign in/i });
    expect(link).toHaveAttribute("href", "/login");
  });

  it("shows error when passwords do not match", async () => {
    const user = userEvent.setup();

    renderWithRouter(<RegisterPage />);
    await user.type(screen.getByLabelText(/^name$/i), "Test User");
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "password123");
    await user.type(
      screen.getByLabelText(/confirm password/i),
      "differentpass",
    );
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    });
  });

  it("shows error toast on failed registration", async () => {
    server.use(
      http.post("/api/auth/register", () =>
        HttpResponse.json(
          { detail: "Email already registered" },
          { status: 409 },
        ),
      ),
    );
    const user = userEvent.setup();

    renderWithRouter(<RegisterPage />);
    await user.type(screen.getByLabelText(/^name$/i), "Test User");
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "password123");
    await user.type(screen.getByLabelText(/confirm password/i), "password123");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText("Email already registered")).toBeInTheDocument();
    });
  });

  it("navigates to login on successful registration", async () => {
    server.use(
      http.post("/api/auth/register", () =>
        HttpResponse.json(
          {
            id: 1,
            name: "Test User",
            email: "test@example.com",
            created_at: "2026-01-01T00:00:00Z",
          },
          { status: 201 },
        ),
      ),
    );
    const user = userEvent.setup();

    renderWithRouter(<RegisterPage />);
    await user.type(screen.getByLabelText(/^name$/i), "Test User");
    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "password123");
    await user.type(screen.getByLabelText(/confirm password/i), "password123");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/login");
    });
  });
});
