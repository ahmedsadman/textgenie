import axios from "axios";

import type {
  Bank,
  Category,
  MetadataBlacklist,
  PaginatedMessages,
  PaginatedTransactions,
  User,
  WebhookSettings,
} from "@/lib/types";

export interface BankUpdate {
  name?: string;
  last_balance?: string;
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

  getBanks: () => client.get<Bank[]>("/banks").then((r) => r.data),

  createBank: (name: string) =>
    client.post<Bank>("/banks", { name }).then((r) => r.data),

  updateBank: (id: number, data: BankUpdate) =>
    client.put<Bank>(`/banks/${id}`, data).then((r) => r.data),

  deleteBank: (id: number) =>
    client.delete<void>(`/banks/${id}`).then((r) => r.data),

  getTransactions: (params: TransactionsQuery) =>
    client
      .get<PaginatedTransactions>("/transactions", { params })
      .then((r) => r.data),
};
