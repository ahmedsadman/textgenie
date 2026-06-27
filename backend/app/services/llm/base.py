from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

TransactionType = Literal["income", "expense"]


@dataclass
class MetadataResult:
    bank: str | None = None
    balance: Decimal | None = None
    amount: Decimal | None = None
    transaction_type: TransactionType | None = None


@dataclass
class ParsePrompt:
    system_instruction: str
    contents: str


_CATEGORIZE_SYSTEM = """\
You are an SMS message classifier. Given an SMS message, pick the single best category from the user-provided list, or return null if none fit.
The message may be in any language (English, Bengali, Arabic, Chinese, etc.). Interpret based on content meaning regardless of language.

Examples (these use illustrative category names — always use the categories provided by the user, not the example ones):
- Message from "BRACBANK": "Your account has been debited 50.00 BDT. Balance: 2000 BDT" -> category: "transaction"
- Message from "+99002291": "Happy birthday!" -> category: "personal"
- Message from "+80881092213": "আপনার একাউন্ট থেকে ৬০০ টাকা কেটে নেওয়া হয়েছে" -> category: "transaction"
- Message from "Daraz": "Win a free iPhone now!" -> category: "promotion"
- Message from "STARCINEPLEX": "Your ticket is confirmed for Dune on 12th June. Seats: D1, D2" -> category: "ticket"

Respond with this exact JSON object:
{"category": "<category_name>"|null}
Rules:
- Use a name from the Categories list, exactly as written. Never invent new names.
- Return null if no category fits.\
"""


_METADATA_SYSTEM = """\
You are a SMS metadata extractor. The user owns a list of banks. Given an SMS message, identify which of those banks the SMS is from (if any), the latest balance mentioned, and any single transaction in the message (amount and direction).
The message may be in any language. Interpret based on content meaning regardless of language.

Examples (these use illustrative bank names — always use the bank names provided by the user, not the example ones):
- Message from "BRACBANK": "Acct debit 50.00 BDT. Balance: 2000 BDT" with Banks ["BRAC Bank PLC"] -> bank: "BRAC Bank PLC", balance: 2000, amount: 50.00, transaction_type: "expense"
- Message from "EBL": "POS Transaction Amount: 3500 BDT Balance: 100000 BDT" with Banks ["EBL", "City Bank"] -> bank: "EBL", balance: 100000, amount: 3500, transaction_type: "expense"
- Message from "+88019921": "CITYTOUCH credited Amount: 5000 BDT Balance: 100000.00 BDT" with Banks ["EBL", "City Bank"] -> bank: "City Bank", balance: 100000.00, amount: 5000, transaction_type: "income"
- Message from "BRACBANK": "Your statement is ready. Balance: 2000 BDT" with Banks ["BRAC Bank PLC"] -> bank: "BRAC Bank PLC", balance: 2000, amount: null, transaction_type: null
- Message from "Daraz": "Sale starts now!" with Banks ["BRAC Bank PLC"] -> bank: null, balance: null, amount: null, transaction_type: null
- Message from "bKash": "You have received deposit from iBanking of Tk 2,000.00 from City Bank. Fee Tk 0.00. Balance Tk 2,082.19. TrxID DFO7MSENKP" with Banks ["BRAC Bank PLC", "City Bank"] -> bank: null, balance: null, amount: null, transaction_type: null

Respond with this exact JSON object:
{"bank": "<bank_name>"|null, "balance": <number>|null, "amount": <number>|null, "transaction_type": "income"|"expense"|null}
Rules:
- bank: use a name from the Banks list, exactly as written, or null. Never invent new names.
- balance: a plain number (no currency symbol, no commas, no thousands separators), or null. Only set when you have also identified a bank.
- amount: a plain positive number representing the transaction value, or null. Only set when you have also identified a bank AND the message describes a single concrete transaction (debit, credit, withdrawal, deposit, transfer, payment).
- transaction_type: "expense" when funds leave the account (debit, withdrawal, payment, purchase); "income" when funds enter (credit, deposit, refund, salary). Null when no transaction is described or direction is ambiguous.
- amount and transaction_type must either both be set or both be null.\
"""


class LLMProvider(ABC):
    def build_categorize_prompt(
        self, content: str, sender: str, categories: list[str]
    ) -> ParsePrompt:
        categories_str = ", ".join(f'"{c}"' for c in categories)
        contents = (
            f"Categorize the message into one of the categories below.\n"
            f"Categories: [{categories_str}]\n\n"
            f'Message from "{sender}":\n"{content}"'
        )
        return ParsePrompt(system_instruction=_CATEGORIZE_SYSTEM, contents=contents)

    def build_metadata_prompt(
        self, content: str, sender: str, banks: list[str]
    ) -> ParsePrompt:
        banks_str = ", ".join(f'"{b}"' for b in banks)
        contents = (
            f"The user owns the following banks. If the message appears to be from one of "
            f"these banks (based on sender or content), identify the bank and extract the "
            f"latest balance mentioned in the message.\n"
            f"Banks: [{banks_str}]\n\n"
            f'Message from "{sender}":\n"{content}"'
        )
        return ParsePrompt(system_instruction=_METADATA_SYSTEM, contents=contents)

    @abstractmethod
    def categorize(
        self, content: str, sender: str, categories: list[str]
    ) -> str | None:
        """Return the matching category name, or None if no category fits."""
        ...

    @abstractmethod
    def extract_metadata(
        self, content: str, sender: str, banks: list[str]
    ) -> MetadataResult:
        """Return the bank + balance extracted from the message."""
        ...
