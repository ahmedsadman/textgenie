import re
from decimal import Decimal, InvalidOperation

from app.models import Bank

VARIABLE_PATTERN = re.compile(r"\{\{balance\}\}")
_NUMBER_RE = r"(\d+(?:\.\d+)?)"


def normalize(text: str) -> str:
    text = text.replace("\n", " ")
    text = text.replace(",", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def template_to_regex(template: str) -> re.Pattern[str]:
    parts = VARIABLE_PATTERN.split(template)
    regex_parts: list[str] = []
    variables = VARIABLE_PATTERN.findall(template)

    for i, part in enumerate(parts):
        regex_parts.append(re.escape(part))
        if i < len(variables):
            regex_parts.append(_NUMBER_RE)

    return re.compile("".join(regex_parts))


def extract_bank_data(
    sender: str,
    content: str,
    banks: list[Bank],
) -> tuple[Bank, Decimal] | None:
    normalized = normalize(content)
    sender_lower = sender.lower()

    for bank in banks:
        matched = any(s.name.lower() == sender_lower for s in bank.senders)
        if not matched:
            continue

        for bt in bank.templates:
            pattern = template_to_regex(bt.template)
            m = pattern.search(normalized)
            if m:
                try:
                    balance = Decimal(m.group(1))
                except (InvalidOperation, IndexError):
                    continue
                return bank, balance

    return None
