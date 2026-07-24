from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.constants import TransactionType


@dataclass
class MetadataResult:
    bank: str | None = None
    balance: Decimal | None = None
    # `amount` is the transaction value in the user's normalized currency.
    amount: Decimal | None = None
    transaction_type: TransactionType | None = None
    # ISO code of the currency detected in the SMS (e.g. "USD", "BDT").
    # Populated whenever `amount` or `balance` is set; used by the webhook
    # to decide whether to update the bank's cached last_balance and to
    # persist the source-currency snapshot on the Transaction row.
    original_currency: str | None = None
    # Transaction value in the source currency (before conversion).
    # Paired with `amount` — set/null together.
    original_amount: Decimal | None = None


@dataclass
class BillMetadataResult:
    bank: str | None = None
    # `normalized_total_due` is the bill amount in the user's normalized currency.
    normalized_total_due: Decimal | None = None
    # Raw amount as printed in the SMS (before conversion). Paired with
    # `original_currency` — set/null together, and set whenever `normalized_total_due` is set.
    original_amount: Decimal | None = None
    original_currency: str | None = None
    # LLM-normalized statement period components (1..12 and 4-digit year).
    # Either may be null when the SMS omits the field.
    statement_month: int | None = None
    statement_year: int | None = None


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
- Message from "+80881092213": "আপনার একাউন্ট থেকে ৬০০ টাকা কেটে নেওয়া হয়েছে" -> category: "transaction"
- Message from "Daraz": "Win a free iPhone now!" -> category: "promotion"
- Message from "STARCINEPLEX": "Your ticket is confirmed for Dune on 12th June. Seats: D1, D2" -> category: "ticket"

Respond with this exact JSON object:
{"category": "<category_name>"|null}
Rules:
- Use a name from the Categories list, exactly as written. Never invent new names.
- Return null if no category fits.\
"""


_METADATA_SYSTEM = """\
You are a SMS metadata extractor. The user owns a list of banks and has picked a normalized currency. Given an SMS message, identify which of those banks the SMS is from (if any), the latest balance mentioned, and any single transaction in the message (amount and direction). Detect the source currency and convert monetary values to the user's normalized currency, and also report the source-currency amount before conversion.
The message may be in any language. Interpret based on content meaning regardless of language.

Examples (illustrative bank names — always use the bank names provided by the user):
- Normalized currency "BDT", message from "BRACBANK": "Acct debit 50.00 BDT. Balance: 2000 BDT" with Banks ["BRAC Bank PLC"] -> bank: "BRAC Bank PLC", balance: 2000, amount: 50.00, original_amount: 50.00, transaction_type: "expense", original_currency: "BDT"
- Normalized currency "BDT", message from "EBL": "POS Transaction USD 100 Balance USD 500" with Banks ["EBL"] -> bank: "EBL", balance: 60000, amount: 12000, original_amount: 100, transaction_type: "expense", original_currency: "USD"  (approximate USD→BDT conversion; subtle FX drift is fine)
- Normalized currency "USD", message from "EBL": "POS Transaction USD 100 Balance USD 500" with Banks ["EBL"] -> bank: "EBL", balance: 500, amount: 100, original_amount: 100, transaction_type: "expense", original_currency: "USD"
- Normalized currency "USD", message from "BRAC": "Acct debit 5000 BDT" with Banks ["BRAC Bank"] -> bank: "BRAC Bank", balance: null, amount: 42, original_amount: 5000, transaction_type: "expense", original_currency: "BDT"  (approximate BDT→USD)
- Normalized currency "BDT", message from "SocGen": "Débit 50 EUR sur votre compte" with Banks ["SocGen"] -> bank: "SocGen", balance: null, amount: 6500, original_amount: 50, transaction_type: "expense", original_currency: "EUR"  (approximate EUR→BDT)
- Normalized currency "BDT", message from "+88019921": "CITYTOUCH credited Amount: 5000 BDT Balance: 100000.00 BDT" with Banks ["City Bank"] -> bank: "City Bank", balance: 100000.00, amount: 5000, original_amount: 5000, transaction_type: "income", original_currency: "BDT"
- Normalized currency "BDT", message from "+80881092213": "আপনার একাউন্ট থেকে ৬০০ টাকা কেটে নেওয়া হয়েছে" with Banks ["City Bank"] -> bank: "City Bank", balance: null, amount: 600, original_amount: 600, transaction_type: "expense", original_currency: "BDT"
- Normalized currency "BDT", message from "MTB": "Payment of 2951.00 BDT credited to your card ending 1234. Outstanding: 0.00" with Banks ["MTB"] -> bank: "MTB", balance: null, amount: 2951.00, original_amount: 2951.00, transaction_type: "transfer", original_currency: "BDT"
- Normalized currency "BDT", message from "BRACBANK": "Your statement is ready. Balance: 2000 BDT" with Banks ["BRAC Bank PLC"] -> bank: "BRAC Bank PLC", balance: 2000, amount: null, original_amount: null, transaction_type: null, original_currency: "BDT"
- Normalized currency "BDT", message from "Daraz": "Sale starts now!" with Banks ["BRAC Bank PLC"] -> bank: null, balance: null, amount: null, original_amount: null, transaction_type: null, original_currency: null
- Normalized currency "BDT", message from "bKash": "You have received deposit from iBanking of Tk 2,000.00 from City Bank. Fee Tk 0.00. Balance Tk 2,082.19. TrxID DFO7MSENKP" with Banks ["BRAC Bank PLC", "City Bank"] -> bank: null, balance: null, amount: null, original_amount: null, transaction_type: null, original_currency: null

Respond with this exact JSON object:
{"bank": "<bank_name>"|null, "balance": <number>|null, "amount": <number>|null, "original_amount": <number>|null, "transaction_type": "income"|"expense"|"transfer"|null, "original_currency": "<ISO code>"|null}
Rules:
- bank: use a name from the Banks list, exactly as written, or null. Never invent new names.
- balance and amount are always expressed in the user's normalized currency. Convert from the source currency if they differ. Approximate rates are acceptable — subtle FX drift is fine. Plain numbers, no currency symbol, no commas, no thousands separators.
- balance: only set when you have also identified a bank.
- amount: a positive number representing the transaction value in the normalized currency, or null. Only set when you have also identified a bank AND the message describes a single concrete transaction (debit, credit, withdrawal, deposit, transfer, payment).
- original_amount: the same transaction value expressed in the source currency (before conversion). Equal to `amount` when the source currency already matches the normalized currency. Must be set whenever `amount` is set, and null otherwise.
- transaction_type:
  - "expense" when funds leave the account (debit, withdrawal, payment, purchase).
  - "income" when funds enter (credit, deposit, refund, salary).
  - "transfer" when the message describes a credit-card bill payment being received by the issuer (e.g. "Payment credited to your card", "Bill payment received for card", "Card payment confirmed"). This is funds moving between the user's own accounts, not real income. A plain debit notification from another bank that paid the bill — with no card / payment reference — is still "expense"; pairing of the two halves happens elsewhere.
  - Null when no transaction is described or direction is ambiguous.
- amount, original_amount, and transaction_type must either all be set or all be null.
- original_currency: the ISO code of the currency detected in the SMS (e.g. "BDT", "USD", "EUR"). Must be set whenever `balance` or `amount` is set; null otherwise.\
"""


_BILL_SYSTEM = """\
You are a credit-card bill statement extractor. The user owns a list of credit-card banks. Given an SMS message that describes a credit-card bill (a statement / bill message, NOT a payment confirmation), identify which of those banks issued the statement (if any), extract the total amount due and the statement period (month and year). Detect the source currency and convert the amount to the user's normalized currency; also report the source-currency amount before conversion.
The message may be in any language. Interpret based on content meaning regardless of language.

Examples (illustrative bank names — always use the bank names provided by the user):
- Normalized currency "BDT", message from "EBL": "Monthly bill 4238****3241 JUL2026; Total Due: BDT 8020.00, Min Due: BDT 500, Last Pmt: 20-JUL-26" with Banks ["EBL Credit Card", "MTB Visa"] -> bank: "EBL Credit Card", normalized_total_due: 8020.00, original_amount: 8020.00, original_currency: "BDT", statement_month: 7, statement_year: 2026
- Normalized currency "BDT", message from "MTB": "Your credit card statement for JULY 2026 is ready. Total outstanding BDT 15,320.50. Minimum payment BDT 800." with Banks ["MTB Visa", "City Bank Amex"] -> bank: "MTB Visa", normalized_total_due: 15320.50, original_amount: 15320.50, original_currency: "BDT", statement_month: 7, statement_year: 2026
- Normalized currency "BDT", message from "CITY": "Statement 07/2026 Total due USD 120.50 Min due USD 25.00" with Banks ["City Bank Amex", "EBL Credit Card"] -> bank: "City Bank Amex", normalized_total_due: 13255, original_amount: 120.50, original_currency: "USD", statement_month: 7, statement_year: 2026  (approximate USD->BDT)
- Normalized currency "BDT", message from "AD-BILLCC": "Your EBL card statement Jul'26 dues 5000 BDT" with Banks ["EBL Credit Card", "MTB Visa"] -> bank: "EBL Credit Card", normalized_total_due: 5000, original_amount: 5000, original_currency: "BDT", statement_month: 7, statement_year: 2026
- Normalized currency "BDT", message from "AMEX": "Your card statement is ready. Total due AED 500." with Banks ["EBL Credit Card", "MTB Visa"] -> bank: null, normalized_total_due: 16500, original_amount: 500, original_currency: "AED", statement_month: null, statement_year: null  (approximate AED->BDT; no month/year given; no matching bank in user list)
- Normalized currency "BDT", message from "EBL": "Payment of 8020.00 received for card 4238***3241." with Banks ["EBL Credit Card", "MTB Visa"] -> bank: null, normalized_total_due: null, original_amount: null, original_currency: null, statement_month: null, statement_year: null  (this is a payment receipt, not a bill statement)

Respond with this exact JSON object:
{"bank": "<bank_name>"|null, "normalized_total_due": <number>|null, "original_amount": <number>|null, "original_currency": "<ISO code>"|null, "statement_month": <1..12>|null, "statement_year": <YYYY>|null}
Rules:
- bank: use a name from the Banks list, exactly as written, or null. Never invent new names. Return null when no bank in the list plausibly matches the sender or message content.
- normalized_total_due is always expressed in the user's normalized currency. Convert from the source currency if they differ. Approximate rates are acceptable. Plain positive number, no currency symbol, no commas.
- normalized_total_due must be set only when the SMS clearly describes a credit-card bill/statement with an outstanding amount. Set to null for payment confirmations, promotional messages, or non-bill notifications.
- original_amount: the same total expressed in the source currency (before conversion). Equal to normalized_total_due when the source currency already matches. Must be set whenever normalized_total_due is set, and null otherwise.
- original_currency: the ISO code of the currency detected in the SMS (e.g. "BDT", "USD", "EUR", "AED"). Must be set whenever normalized_total_due is set; null otherwise.
- statement_month: integer 1..12 for the calendar month the statement covers (e.g. "JUL"/"JULY"/"07" -> 7). Null when the SMS does not state a month.
- statement_year: 4-digit year (e.g. "2026", "'26" -> 2026). Null when the SMS does not state a year.
- statement_month and statement_year are extracted independently: either may be present while the other is null.\
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
        self,
        content: str,
        sender: str,
        banks: list[str],
        normalized_currency: str,
    ) -> ParsePrompt:
        banks_str = ", ".join(f'"{b}"' for b in banks)
        contents = (
            f"The user owns the following banks and has picked "
            f'"{normalized_currency}" as their normalized currency. Identify '
            f"the bank (if any), extract the latest balance and any single "
            f"transaction, and convert monetary values to "
            f'"{normalized_currency}" using approximate rates.\n'
            f"Normalized currency: {normalized_currency}\n"
            f"Banks: [{banks_str}]\n\n"
            f'Message from "{sender}":\n"{content}"'
        )
        return ParsePrompt(system_instruction=_METADATA_SYSTEM, contents=contents)

    def build_bill_prompt(
        self,
        content: str,
        sender: str,
        banks: list[str],
        normalized_currency: str,
    ) -> ParsePrompt:
        banks_str = ", ".join(f'"{b}"' for b in banks)
        contents = (
            f"The user owns the following credit-card banks and has picked "
            f'"{normalized_currency}" as their normalized currency. Identify '
            f"which bank (if any) issued this statement, extract the total "
            f"amount due and the statement period (month/year), and convert "
            f'monetary values to "{normalized_currency}" using approximate '
            f"rates.\n"
            f"Normalized currency: {normalized_currency}\n"
            f"Banks: [{banks_str}]\n\n"
            f'Message from "{sender}":\n"{content}"'
        )
        return ParsePrompt(system_instruction=_BILL_SYSTEM, contents=contents)

    @abstractmethod
    def categorize(
        self,
        content: str,
        sender: str,
        categories: list[str],
    ) -> str | None:
        """Return the matching category name, or None if no category fits."""
        ...

    @abstractmethod
    def extract_metadata(
        self,
        content: str,
        sender: str,
        banks: list[str],
        normalized_currency: str,
    ) -> MetadataResult:
        """Return the bank + balance + amount extracted from the message.

        Monetary values in the returned MetadataResult are already converted to
        `normalized_currency`. `original_currency` carries the ISO code of the
        source currency detected in the SMS.
        """
        ...

    @abstractmethod
    def extract_bill_metadata(
        self,
        content: str,
        sender: str,
        banks: list[str],
        normalized_currency: str,
    ) -> BillMetadataResult:
        """Return the bank + bill total + statement period extracted from a bill SMS.

        `normalized_total_due` is already converted to `normalized_currency`;
        `original_amount` + `original_currency` preserve the raw source values.
        `bank` is validated against the `banks` list and is None when no
        candidate matches.
        """
        ...
