import { generatePaginationItems } from "./pagination";

function toSimple(
  items: ReturnType<typeof generatePaginationItems>,
): (number | "...")[] {
  return items.map((i) => (i.type === "ellipsis" ? "..." : i.page));
}

describe("generatePaginationItems", () => {
  it("returns all pages when totalPages <= 7", () => {
    expect(toSimple(generatePaginationItems(1, 5))).toEqual([1, 2, 3, 4, 5]);
    expect(toSimple(generatePaginationItems(3, 7))).toEqual([
      1, 2, 3, 4, 5, 6, 7,
    ]);
  });

  it("shows right ellipsis when current page is near the start", () => {
    expect(toSimple(generatePaginationItems(1, 10))).toEqual([1, 2, "...", 10]);
    expect(toSimple(generatePaginationItems(2, 10))).toEqual([
      1,
      2,
      3,
      "...",
      10,
    ]);
  });

  it("shows left ellipsis when current page is near the end", () => {
    expect(toSimple(generatePaginationItems(10, 10))).toEqual([
      1,
      "...",
      9,
      10,
    ]);
    expect(toSimple(generatePaginationItems(9, 10))).toEqual([
      1,
      "...",
      8,
      9,
      10,
    ]);
  });

  it("shows both ellipses when current page is in the middle", () => {
    expect(toSimple(generatePaginationItems(5, 10))).toEqual([
      1,
      "...",
      4,
      5,
      6,
      "...",
      10,
    ]);
  });

  it("handles single page", () => {
    expect(toSimple(generatePaginationItems(1, 1))).toEqual([1]);
  });

  it("omits ellipsis when gap is exactly one", () => {
    expect(toSimple(generatePaginationItems(3, 8))).toEqual([
      1,
      2,
      3,
      4,
      "...",
      8,
    ]);
  });
});
