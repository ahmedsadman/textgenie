import axios from "axios";

import type {
  AccountType,
  Bank,
  Bill,
  Category,
  Currency,
  CurrencySettings,
  Message,
  MetadataBlacklist,
  PaginatedBills,
  PaginatedMessages,
  PaginatedTransactions,
  Transaction,
  TransactionType,
  User,
  WebhookSettings,
} from "@/lib/types";

export interface BankCreate {
  name: string;
  account_type?: AccountType;
  card_digits?: string | null;
}

export interface BankUpdate {
  name?: string;
  last_balance?: string;
  account_type?: AccountType;
  card_digits?: string | null;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const client = axios.create({
  baseURL: "/api",
  withCredentials: true,
  paramsSerializer: { indexes: null },
});

client.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status ?? 0;
      const data = error.response?.data as { detail?: string } | undefined;
      throw new ApiError(status, data?.detail ?? "Request failed");
    }
    throw error;
  },
);

export interface MessagesQuery {
  page: number;
  page_size: number;
  category_ids?: number[];
  search?: string;
}

export interface TransactionsQuery {
  page: number;
  page_size: number;
  from_date?: string;
  to_date?: string;
}

export interface BillsQuery {
  page: number;
  page_size: number;
  bank_id?: number;
  from_date?: string;
  to_date?: string;
}

export const api = {
  login: (email: string, password: string) =>
    client.post<User>("/auth/login", { email, password }).then((r) => r.data),

  register: (name: string, email: string, password: string) =>
    client
      .post<User>("/auth/register", { name, email, password })
      .then((r) => r.data),

  getMe: () => client.get<User>("/auth/me").then((r) => r.data),

  logout: () => client.post<void>("/auth/logout", {}).then((r) => r.data),

  getCategories: () =>
    client.get<Category[]>("/categories").then((r) => r.data),

  createCategory: (name: string) =>
    client.post<Category>("/categories", { name }).then((r) => r.data),

  updateCategory: (id: number, name: string) =>
    client.put<Category>(`/categories/${id}`, { name }).then((r) => r.data),

  deleteCategory: (id: number) =>
    client.delete<void>(`/categories/${id}`).then((r) => r.data),

  getMessages: (params: MessagesQuery) =>
    client.get<PaginatedMessages>("/messages", { params }).then((r) => r.data),

  getMessage: (id: number) =>
    client.get<Message>(`/messages/${id}`).then((r) => r.data),

  getMessageSenders: () =>
    client.get<string[]>("/messages/senders").then((r) => r.data),

  deleteMessage: (id: number) =>
    client.delete<void>(`/messages/${id}`).then((r) => r.data),

  getWebhookSettings: () =>
    client.get<WebhookSettings>("/settings/webhook").then((r) => r.data),

  regenerateWebhookToken: () =>
    client
      .post<WebhookSettings>("/settings/webhook/regenerate", {})
      .then((r) => r.data),

  getMetadataBlacklist: () =>
    client
      .get<MetadataBlacklist>("/settings/metadata-blacklist")
      .then((r) => r.data),

  updateMetadataBlacklist: (senders: string[]) =>
    client
      .put<MetadataBlacklist>("/settings/metadata-blacklist", { senders })
      .then((r) => r.data),

  getCurrency: () =>
    client.get<CurrencySettings>("/settings/currency").then((r) => r.data),

  updateCurrency: (currency: Currency) =>
    client
      .put<CurrencySettings>("/settings/currency", { currency })
      .then((r) => r.data),

  getBanks: () => client.get<Bank[]>("/banks").then((r) => r.data),

  createBank: (data: BankCreate) =>
    client.post<Bank>("/banks", data).then((r) => r.data),

  updateBank: (id: number, data: BankUpdate) =>
    client.patch<Bank>(`/banks/${id}`, data).then((r) => r.data),

  deleteBank: (id: number) =>
    client.delete<void>(`/banks/${id}`).then((r) => r.data),

  getTransactions: (params: TransactionsQuery) =>
    client
      .get<PaginatedTransactions>("/transactions", { params })
      .then((r) => r.data),

  updateTransaction: (id: number, type: TransactionType) =>
    client
      .patch<Transaction>(`/transactions/${id}`, { type })
      .then((r) => r.data),

  getBills: (params: BillsQuery) =>
    client.get<PaginatedBills>("/bills", { params }).then((r) => r.data),

  getBill: (id: number) => client.get<Bill>(`/bills/${id}`).then((r) => r.data),

  unlinkBillPayments: (id: number, transaction_ids: number[]) =>
    client
      .patch<Bill>(`/bills/${id}`, { unlink_transaction_ids: transaction_ids })
      .then((r) => r.data),
};
