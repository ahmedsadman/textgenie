import React from "react";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SummaryGraphSection from "@/components/SummaryGraphSection";
import { server } from "@/mocks/server";
import { renderWithQueryClient } from "@/test-utils";

// recharts' ResponsiveContainer renders 0x0 in jsdom, so the chart never mounts.
// Give it concrete dimensions so the chart wrapper renders. The chart body
// (axes/series tspans) still won't lay out in jsdom, so assertions target
// layout-independent, user-visible state: the heading, the range-picker label,
// the empty state, and that the empty state is absent once the chart mounts.
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({
      children,
    }: {
      children: React.ReactElement<{ width?: number; height?: number }>;
    }) => React.cloneElement(children, { width: 800, height: 400 }),
  };
});

const seriesResponse = {
  series: [
    { month_start: "2025-01-01", income: "150.00", expense: "30.00" },
    { month_start: "2025-02-01", income: "200.00", expense: "80.00" },
  ],
};

const EMPTY_STATE = /no transactions in selected range\./i;

describe("SummaryGraphSection", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders the heading and the default 'Last year' range label", () => {
    server.use(
      http.get("/api/transactions/summary", () =>
        HttpResponse.json({ series: [] }),
      ),
    );

    renderWithQueryClient(<SummaryGraphSection />);

    expect(screen.getByText("Summary Graph")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /select date range/i }),
    ).toHaveTextContent(/last year/i);
  });

  it("shows the empty state when the summary has no data", async () => {
    server.use(
      http.get("/api/transactions/summary", () =>
        HttpResponse.json({ series: [] }),
      ),
    );

    renderWithQueryClient(<SummaryGraphSection />);

    await waitFor(() => {
      expect(screen.getByText(EMPTY_STATE)).toBeInTheDocument();
    });
  });

  it("renders the chart (no empty state) when series data is present", async () => {
    server.use(
      http.get("/api/transactions/summary", () =>
        HttpResponse.json(seriesResponse),
      ),
    );

    const { container } = renderWithQueryClient(<SummaryGraphSection />);

    // Once the query resolves with data, the empty state is gone and the
    // recharts wrapper is mounted.
    await waitFor(() => {
      expect(container.querySelector(".recharts-wrapper")).toBeInTheDocument();
    });
    expect(screen.queryByText(EMPTY_STATE)).not.toBeInTheDocument();
  });

  it("changing the range updates the label and persists to localStorage", async () => {
    server.use(
      http.get("/api/transactions/summary", () =>
        HttpResponse.json({ series: [] }),
      ),
    );

    const user = userEvent.setup();
    renderWithQueryClient(<SummaryGraphSection />);

    const trigger = screen.getByRole("button", { name: /select date range/i });
    expect(trigger).toHaveTextContent(/last year/i);

    await user.click(trigger);

    const presetsHeading = await screen.findByText("Presets");
    await user.click(
      within(presetsHeading.parentElement as HTMLElement).getByRole("button", {
        name: /last 3 months/i,
      }),
    );

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /select date range/i }),
      ).toHaveTextContent(/last 3 months/i);
    });

    const persisted = localStorage.getItem("finance.summaryRange");
    expect(persisted).not.toBeNull();
    expect(JSON.parse(persisted as string)).toMatchObject({
      presetKey: "last_3_months",
    });
  });
});
