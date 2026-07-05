import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils";
import type { DateRangeSelection } from "@/lib/dateRange";

import DateRangePicker from "./DateRangePicker";

function Harness({ initial }: { initial: DateRangeSelection }) {
  const [value, setValue] = useState<DateRangeSelection>(initial);
  return <DateRangePicker value={value} onChange={setValue} />;
}

describe("DateRangePicker", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 6, 15, 12, 0, 0));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("highlights the resolved range on the calendar after picking a preset", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderWithQueryClient(
      <Harness initial={{ presetKey: "all_time", customRange: null }} />,
    );

    await user.click(
      screen.getByRole("button", { name: /select date range/i }),
    );
    await user.click(screen.getByText("This month"));

    // Popover closed; reopen to inspect the calendar highlight.
    await user.click(
      screen.getByRole("button", { name: /select date range/i }),
    );

    // "This month" for July 2026 spans 15 days (1st through 15th).
    // react-day-picker marks range cells with aria-selected="true".
    const selectedDays = document.querySelectorAll('[aria-selected="true"]');
    expect(selectedDays.length).toBeGreaterThanOrEqual(15);
  });

  it("shows a 'Select end date' hint after clicking a start date", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderWithQueryClient(
      <Harness initial={{ presetKey: "all_time", customRange: null }} />,
    );

    await user.click(
      screen.getByRole("button", { name: /select date range/i }),
    );
    // Two months render side-by-side; click the first day button labeled "10".
    const tenButtons = screen
      .getAllByRole("button")
      .filter((el) => el.textContent === "10");
    await user.click(tenButtons[0]);

    expect(screen.getByText(/select end date/i)).toBeInTheDocument();
  });
});
