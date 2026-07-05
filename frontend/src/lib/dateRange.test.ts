import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resolveDateRange } from "./dateRange";

describe("resolveDateRange", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns first-of-month through end-of-today for this_month", () => {
    vi.setSystemTime(new Date(2026, 6, 15, 10, 30, 0));

    const { from, to } = resolveDateRange({
      presetKey: "this_month",
      customRange: null,
    });

    const fromDate = new Date(from!);
    const toDate = new Date(to!);

    expect(fromDate.getFullYear()).toBe(2026);
    expect(fromDate.getMonth()).toBe(6);
    expect(fromDate.getDate()).toBe(1);
    expect(fromDate.getHours()).toBe(0);
    expect(fromDate.getMinutes()).toBe(0);
    expect(fromDate.getSeconds()).toBe(0);

    expect(toDate.getFullYear()).toBe(2026);
    expect(toDate.getMonth()).toBe(6);
    expect(toDate.getDate()).toBe(15);
    expect(toDate.getHours()).toBe(23);
    expect(toDate.getMinutes()).toBe(59);
    expect(toDate.getSeconds()).toBe(59);
  });

  it("uses the first day when today is the first of the month", () => {
    vi.setSystemTime(new Date(2026, 0, 1, 8, 0, 0));

    const { from, to } = resolveDateRange({
      presetKey: "this_month",
      customRange: null,
    });

    const fromDate = new Date(from!);
    const toDate = new Date(to!);

    expect(fromDate.getMonth()).toBe(0);
    expect(fromDate.getDate()).toBe(1);
    expect(toDate.getDate()).toBe(1);
  });
});
