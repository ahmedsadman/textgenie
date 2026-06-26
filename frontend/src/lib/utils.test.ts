import { formatMessageDateTime } from "@/lib/utils";

// Build a local-time date so the assertion isn't sensitive to the runner's TZ.
function localDate(
  y: number,
  m: number, // 1-based month for readability at the call site
  d: number,
  h = 0,
  min = 0,
): string {
  return new Date(y, m - 1, d, h, min).toISOString();
}

describe("formatMessageDateTime — live current year (no fake timers)", () => {
  it("omits the year for a date in the real current year", () => {
    const now = new Date();
    const sample = new Date(
      now.getFullYear(),
      5, // June
      27,
      2,
      11,
    ).toISOString();
    expect(formatMessageDateTime(sample)).toBe("27th June at 2:11 AM");
  });
});

describe("formatMessageDateTime", () => {
  // Pin "today" so current-year-omission cases are deterministic regardless
  // of when the suite runs.
  beforeAll(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 5, 27, 12, 0));
  });

  afterAll(() => {
    vi.useRealTimers();
  });

  describe("year omitted when it matches the current year", () => {
    it("renders without a year for a same-year date", () => {
      expect(formatMessageDateTime(localDate(2026, 6, 27, 2, 11))).toBe(
        "27th June at 2:11 AM",
      );
    });

    it("renders with a year for a different-year date", () => {
      expect(formatMessageDateTime(localDate(2024, 6, 27, 2, 11))).toBe(
        "27th June, 2024 at 2:11 AM",
      );
    });
  });

  describe("ordinal suffix", () => {
    // Use a non-current year so every assertion includes the year segment.
    it.each([
      [1, "1st"],
      [2, "2nd"],
      [3, "3rd"],
      [4, "4th"],
      [11, "11th"],
      [12, "12th"],
      [13, "13th"],
      [21, "21st"],
      [22, "22nd"],
      [23, "23rd"],
      [31, "31st"],
    ])("day %i renders with suffix %s", (day, expectedPrefix) => {
      expect(formatMessageDateTime(localDate(2024, 1, day, 9, 5))).toBe(
        `${expectedPrefix} January, 2024 at 9:05 AM`,
      );
    });
  });

  describe("12h clock edge cases", () => {
    it("renders midnight as 12:00 AM", () => {
      expect(formatMessageDateTime(localDate(2024, 1, 5, 0, 0))).toBe(
        "5th January, 2024 at 12:00 AM",
      );
    });

    it("renders noon as 12:00 PM", () => {
      expect(formatMessageDateTime(localDate(2024, 1, 5, 12, 0))).toBe(
        "5th January, 2024 at 12:00 PM",
      );
    });

    it("renders afternoon hours as PM", () => {
      expect(formatMessageDateTime(localDate(2024, 1, 5, 15, 30))).toBe(
        "5th January, 2024 at 3:30 PM",
      );
    });
  });

  it("zero-pads minutes below 10", () => {
    expect(formatMessageDateTime(localDate(2024, 6, 27, 2, 9))).toBe(
      "27th June, 2024 at 2:09 AM",
    );
  });
});
