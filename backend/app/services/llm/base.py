from abc import ABC, abstractmethod


class LLMProvider(ABC):
    def build_categorization_prompt(
        self, content: str, sender: str, categories: list[str]
    ) -> str:
        categories_str = ", ".join(f'"{c}"' for c in categories)
        return f"""\
You are a message categorizer. Given an SMS message and a list of categories, determine which category best fits the message.
The message may be in any language (English, Bengali, Arabic, Chinese, etc.). Categorize based on content meaning regardless of language.

Categories: [{categories_str}]

Examples (these use illustrative category names — always use the categories listed above, not the example ones):
- Message from "BRACBANK": "BRACBNK\nYour account has been debited 50.00 BDT. Balance: 2000 BDT" -> {{"category": "transaction"}}
- Message from "EBL": "ECOMM/POS Transaction\nAmount: 3500 BDT\nMerchant: Aarong\nBalance: 100000 BDT" -> {{"category": "transaction"}}
- Message from "+99002291": "Happy birthday!" -> {{"category": "personal"}}
- Message from "+80881092213": "আপনার একাউন্ট থেকে ৫০০ টাকা কেটে নেওয়া হয়েছে" -> {{"category": "transaction"}}
- Message from "+80881092213": "প্রিন্স বাজার এর সকল আউটলেট এ পাচ্ছেন ৫০% পর্যন্ত ছাড়। ২৬ জুন পর্যন্ত অফার প্রযোজ্য" -> {{"category": "promotion"}}
- Message from "Daraz": "Win a free iPhone now!" -> {{"category": "promotion"}}
- Message from "STARCINEPLEX": "Your ticket is confirmed for Dune on 12th June\nSeat D1, D2" -> {{"category": "ticket"}}

Message from "{sender}":
"{content}"

Respond with a JSON object: {{"category": "<category_name>"}}
If none of the categories fit, respond with: {{"category": "uncategorized"}}

Only use category names from the provided list or "uncategorized"."""

    @abstractmethod
    def categorize_message(
        self, message_content: str, sender: str, categories: list[str]
    ) -> str | None:
        """Return matching category name or None for uncategorized."""
        ...
