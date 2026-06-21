import { screen } from "@testing-library/react";

import DashboardPage from "@/pages/DashboardPage";
import { mockUser, renderWithOutletContext } from "@/test-utils";

describe("DashboardPage", () => {
  it("shows user name and email", () => {
    renderWithOutletContext(<DashboardPage />, { user: mockUser });

    expect(screen.getByText(/test user/i)).toBeInTheDocument();
    expect(screen.getByText("test@example.com")).toBeInTheDocument();
  });

  it("shows dashboard title", () => {
    renderWithOutletContext(<DashboardPage />, { user: mockUser });

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });
});
