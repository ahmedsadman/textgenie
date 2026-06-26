"""Helpers for the per-user metadata-extraction sender blacklist.

The blacklist is stored as a comma-separated string on `User.metadata_blacklist`.
Membership checks are case-insensitive; senders are normalized to lowercase on
write and compared in lowercase on read.
"""

DELIMITER = ","


def parse(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [s.strip().lower() for s in raw.split(DELIMITER) if s.strip()]


def serialize(senders: list[str]) -> str:
    seen: set[str] = set()
    cleaned: list[str] = []
    for s in senders:
        normalized = s.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return DELIMITER.join(cleaned)


def contains(sender: str, raw: str | None) -> bool:
    if not raw or not sender:
        return False
    return sender.strip().lower() in parse(raw)
