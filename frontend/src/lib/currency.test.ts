import { describe, expect, it } from "vitest";

import { formatAmount, formatNumeric } from "@/lib/currency";

describe("formatAmount", () => {
  it("suffixes BDT amounts with the BDT ISO code", () => {
    expect(formatAmount("1500", "BDT")).toBe("1,500.00 BDT");
  });

  it("suffixes USD amounts with the USD ISO code", () => {
    expect(formatAmount(100, "USD")).toBe("100.00 USD");
  });

  it("suffixes EUR amounts with the EUR ISO code", () => {
    expect(formatAmount("42.5", "EUR")).toBe("42.50 EUR");
  });

  it("returns a zero-formatted value for null / undefined input", () => {
    expect(formatAmount(null, "BDT")).toBe("0.00 BDT");
    expect(formatAmount(undefined, "BDT")).toBe("0.00 BDT");
  });

  it("falls back to zero when given a non-numeric string", () => {
    expect(formatAmount("nope", "BDT")).toBe("0.00 BDT");
  });
});

describe("formatNumeric", () => {
  it("emits plain numbers with two decimals and thousand separators", () => {
    expect(formatNumeric("1500")).toBe("1,500.00");
    expect(formatNumeric(0)).toBe("0.00");
  });

  it("handles null / undefined as zero", () => {
    expect(formatNumeric(null)).toBe("0.00");
    expect(formatNumeric(undefined)).toBe("0.00");
  });
});
