export type PaginationItem =
  | { type: "page"; page: number }
  | { type: "ellipsis" };

export function generatePaginationItems(
  currentPage: number,
  totalPages: number,
): PaginationItem[] {
  if (totalPages <= 4) {
    return Array.from({ length: totalPages }, (_, i) => ({
      type: "page" as const,
      page: i + 1,
    }));
  }

  const pages = new Set([1, currentPage, totalPages]);

  const sorted = [...pages].sort((a, b) => a - b);
  const items: PaginationItem[] = [];

  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) {
      items.push({ type: "ellipsis" });
    }
    items.push({ type: "page", page: sorted[i] });
  }

  return items;
}
