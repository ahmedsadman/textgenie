from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class MessageParseResult:
    category: str | None = None
    bank: str | None = None
    balance: Decimal | None = None


@dataclass
class ParsePrompt:
    system_instruction: str
    contents: str


_INTRO = (
    "You are a message parser. Given an SMS message, extract structured information from it.\n"
    "The message may be in any language (English, Bengali, Arabic, Chinese, etc.). "
    "Interpret based on content meaning regardless of language."
)


_CATEGORY_EXAMPLES = """
Examples (these use illustrative category names — always use the categories provided by the user, not the example ones):
- Message from "BRACBANK": "Your account has been debited 50.00 BDT. Balance: 2000 BDT" -> category: "transaction"
- Message from "+99002291": "Happy birthday!" -> category: "personal"
- Message from "+80881092213": "আপনার একাউন্ট থেকে ৫০০ টাকা কেটে নেওয়া হয়েছে" -> category: "transaction"
- Message from "Daraz": "Win a free iPhone now!" -> category: "promotion"
- Message from "MTB Cards": "বিশ্বকাপ উপলক্ষে, এমটিবি ক্রেডিট কার্ডে পার্টনার মার্চেন্ট থেকে ০ শতাংশ EMI-এ TV ক্রয়ে ১০,০০০ পর্যন্ত বোনাস এমরিওয়ার্ডজ পয়েন্টস। বিস্তারিত https://tinyurl.com/bdevyvk3" -> category: "promotion"
- Message from "STARCINEPLEX": "Your ticket is confirmed for Dune on 12th June. Seats: D1, D2" -> category: "ticket"
"""


_BANK_EXAMPLES = """
Examples (these use illustrative bank names — always use the bank names provided by the user, not the example ones):
- Message from "BRACBANK": "Acct debit 50.00 BDT. Balance: 2000 BDT" with Banks ["BRAC Bank PLC"] -> bank: "BRAC Bank PLC", balance: 2000
- Message from "EBL": "POS Transaction Amount: 3500 BDT Balance: 100000 BDT" with Banks ["EBL", "City Bank"] -> bank: "EBL", balance: 100000
- Message from "+88019921": "CITYTOUCH TXN Amount: 3500 BDT Balance: 100000.00 BDT" with Banks ["EBL", "City Bank"] -> bank: "City Bank", balance: 100000.00
- Message from "Daraz": "Sale starts now!" with Banks ["BRAC Bank PLC"] -> bank: null, balance: null
- Message from "bKash": "You have received deposit from iBanking of Tk 2,000.00 from City Bank. Fee Tk 0.00. Balance Tk 2,082.19. TrxID DFO7MSENKP" with Banks ["BRAC Bank PLC", "City Bank"] -> bank: null, balance: null
"""


_RESPONSE_SHAPE = (
    "Respond with this exact JSON object. Set any field to null when it does not apply "
    "or you cannot determine it from the message:\n"
    '{"category": "<category_name>"|null, "bank": "<bank_name>"|null, "balance": <number>|null}\n'
    "Rules:\n"
    "- category: use a name from the Categories list above, or null. Never invent new names.\n"
    "- bank: use a name from the Banks list above, exactly as written, or null. Never invent new names.\n"
    "- balance: a plain number (no currency symbol, no commas, no thousands separators), or null. "
    "Only set when you have also identified a bank.\n"
    "- If the Categories or Banks list was not provided above, the corresponding field MUST be null."
)


class LLMProvider(ABC):
    def build_message_parse_prompt(
        self,
        content: str,
        sender: str,
        categories: list[str],
        banks: list[str] | None = None,
    ) -> ParsePrompt:
        banks = banks or []

        system_sections: list[str] = [_INTRO]
        system_sections.append(_CATEGORY_EXAMPLES)
        system_sections.append(_BANK_EXAMPLES)
        system_sections.append(_RESPONSE_SHAPE)

        user_sections: list[str] = []

        if categories:
            categories_str = ", ".join(f'"{c}"' for c in categories)
            user_sections.append(
                f"Categorize the message into one of the categories below.\n"
                f"Categories: [{categories_str}]"
            )

        if banks:
            banks_str = ", ".join(f'"{b}"' for b in banks)
            user_sections.append(
                f"The user owns the following banks. If the message appears to be from one of "
                f"these banks (based on sender or content), identify the bank and extract the "
                f"latest balance mentioned in the message.\n"
                f"Banks: [{banks_str}]"
            )

        user_sections.append(f'Message from "{sender}":\n"{content}"')

        return ParsePrompt(
            system_instruction="\n\n".join(system_sections),
            contents="\n\n".join(user_sections),
        )

    @abstractmethod
    def parse_message(
        self,
        message_content: str,
        sender: str,
        categories: list[str],
        banks: list[str] | None = None,
    ) -> MessageParseResult:
        """Extract category, bank, and balance from the message."""
        ...
