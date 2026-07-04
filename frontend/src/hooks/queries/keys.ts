import type { TransactionsQuery } from "@/lib/api";

export const bankKeys = {
  all: ["banks"] as const,
  lists: () => [...bankKeys.all, "list"] as const,
};

export const transactionKeys = {
  all: ["transactions"] as const,
  list: (params: TransactionsQuery) =>
    [...transactionKeys.all, "list", params] as const,
};
