import type {
  AdminListUsersQuery,
  AdminUserUsageQuery,
  BillsQuery,
  MessagesQuery,
  TransactionsQuery,
} from "@/lib/api";

export const bankKeys = {
  all: ["banks"] as const,
  lists: () => [...bankKeys.all, "list"] as const,
};

export const transactionKeys = {
  all: ["transactions"] as const,
  list: (params: TransactionsQuery) =>
    [...transactionKeys.all, "list", params] as const,
};

export const billKeys = {
  all: ["bills"] as const,
  list: (params: BillsQuery) => [...billKeys.all, "list", params] as const,
};

export const categoryKeys = {
  all: ["categories"] as const,
  lists: () => [...categoryKeys.all, "list"] as const,
};

export const messageKeys = {
  all: ["messages"] as const,
  list: (params: MessagesQuery) =>
    [...messageKeys.all, "list", params] as const,
};

export const authKeys = {
  all: ["auth"] as const,
  me: () => [...authKeys.all, "me"] as const,
};

export const currencyKeys = {
  all: ["currency"] as const,
  detail: () => [...currencyKeys.all, "detail"] as const,
};

export const adminKeys = {
  all: ["admin"] as const,
  users: () => [...adminKeys.all, "users"] as const,
  usersList: (params: AdminListUsersQuery) =>
    [...adminKeys.users(), params] as const,
  usageSummary: (userIds: number[]) =>
    [...adminKeys.all, "usageSummary", userIds] as const,
  userUsage: (id: number, params: AdminUserUsageQuery) =>
    [...adminKeys.all, "userUsage", id, params] as const,
};
