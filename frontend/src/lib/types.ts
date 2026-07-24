export interface User {
  id: number;
  name: string;
  email: string;
  is_admin: boolean;
  created_at: string;
}

export interface AdminListUsersResponse {
  users: User[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminUsageSummary {
  lifetime_cost_micros: number;
  lifetime_tokens: number;
  last30d_cost_micros: number;
  last30d_tokens: number;
}

export interface AdminUsageBucket {
  bucket_start: string;
  cost_micros: number;
  tokens: number;
}

export interface AdminUserUsageDetailResponse {
  series: AdminUsageBucket[];
  message_count: number;
  bucket: "day" | "week" | "month";
}

export interface Category {
  id: number;
  name: string;
  is_default: boolean;
  created_at: string;
}

export interface Message {
  id: number;
  sender: string;
  content: string;
  received_at: string;
  category: Category | null;
  created_at: string;
}

export interface PaginatedMessages {
  messages: Message[];
  total: number;
  page: number;
  page_size: number;
}

export interface WebhookSettings {
  webhook_url: string;
  webhook_token: string;
}

export interface MetadataBlacklist {
  senders: string[];
}

export type AccountType = "deposit" | "credit";

export interface Bank {
  id: number;
  name: string;
  account_type: AccountType;
  card_digits: string | null;
  last_balance: string | null;
  last_balance_at: string | null;
  created_at: string;
}

export type TransactionType = "income" | "expense" | "transfer";

export type Currency = "BDT" | "USD" | "EUR";

export const CURRENCY_OPTIONS: readonly Currency[] = ["BDT", "USD", "EUR"];

export interface Transaction {
  id: number;
  message_id: number;
  bank_id: number | null;
  bank_name: string | null;
  bank_account_type: AccountType | null;
  sender: string;
  normalized_amount: string;
  normalized_currency: Currency;
  original_amount: string | null;
  original_currency: string | null;
  type: TransactionType;
  date: string;
  paired_with_id: number | null;
  paired_with_message_id: number | null;
  bill_id: number | null;
}

export interface Bill {
  id: number;
  message_id: number;
  sender: string;
  received_at: string;
  bank_id: number | null;
  bank_name: string | null;
  normalized_total_due: string;
  normalized_currency: Currency;
  original_amount: string | null;
  original_currency: string | null;
  statement_period: string | null; // YYYY-MM-DD (first of month)
  paid_at: string | null;
  linked_transaction_ids: number[];
  created_at: string;
}

export interface PaginatedBills {
  bills: Bill[];
  total: number;
  page: number;
  page_size: number;
}

export interface CurrencySettings {
  currency: Currency;
}

export interface TransactionTotals {
  income: string;
  expense: string;
}

export interface PaginatedTransactions {
  transactions: Transaction[];
  total: number;
  page: number;
  page_size: number;
  totals: TransactionTotals;
}
