export interface User {
  id: number;
  name: string;
  email: string;
  created_at: string;
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
