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

export interface Bank {
  id: number;
  name: string;
  last_balance: string | null;
  last_balance_at: string | null;
  created_at: string;
}
