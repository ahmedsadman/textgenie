from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MessageParseResult:
    category: str | None = None


_INTRO = (
    "You are a message categorizer. Given an SMS message, categorize it.\n"
    "The message may be in any language (English, Bengali, Arabic, Chinese, etc.). "
    "Interpret based on content meaning regardless of language."
)


_CATEGORY_EXAMPLES = """
Examples (these use illustrative category names — always use the categories listed above, not the example ones):
- Message from "BRACBANK": "Your account has been debited 50.00 BDT. Balance: 2000 BDT" -> category: "transaction"
- Message from "+99002291": "Happy birthday!" -> category: "personal"
- Message from "+80881092213": "আপনার একাউন্ট থেকে ৫০০ টাকা কেটে নেওয়া হয়েছে" -> category: "transaction"
- Message from "Daraz": "Win a free iPhone now!" -> category: "promotion"
- Message from "MTB Cards": "বিশ্বকাপ উপলক্ষে, এমটিবি ক্রেডিট কার্ডে পার্টনার মার্চেন্ট থেকে ০ শতাংশ EMI-এ TV ক্রয়ে ১০,০০০ পর্যন্ত বোনাস এমরিওয়ার্ডজ পয়েন্টস। বিস্তারিত https://tinyurl.com/bdevyvk3" -> category: "promotion"
- Message from "STARCINEPLEX": "Your ticket is confirmed for Dune on 12th June. Seats: D1, D2" -> category: "ticket"
"""


_RESPONSE_SHAPE = (
    "Respond with this exact JSON object. Set the field to null when it does not apply "
    "or you cannot determine it from the message:\n"
    '{"category": "<category_name>"|null}\n'
    "Rules:\n"
    "- category: use a name from the Categories list above, or null. Never invent new names.\n"
    "- If the Categories list was not provided above, category MUST be null."
)


class LLMProvider(ABC):
    def build_message_parse_prompt(
        self,
        content: str,
        sender: str,
        categories: list[str],
    ) -> str:
        sections: list[str] = [_INTRO]

        if categories:
            categories_str = ", ".join(f'"{c}"' for c in categories)
            sections.append(
                f"Categorize the message into one of the categories below.\n"
                f"Categories: [{categories_str}]"
            )
            sections.append(_CATEGORY_EXAMPLES)

        sections.append(f'Message from "{sender}":\n"{content}"')
        sections.append(_RESPONSE_SHAPE)

        return "\n\n".join(sections)

    @abstractmethod
    def parse_message(
        self,
        message_content: str,
        sender: str,
        categories: list[str],
    ) -> MessageParseResult:
        """Extract category from the message."""
        ...
