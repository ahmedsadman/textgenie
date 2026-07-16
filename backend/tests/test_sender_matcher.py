"""Unit tests for match_bank_by_sender (pure function, no DB)."""

from app.models import Bank
from app.services.banks import match_bank_by_sender


def _bank(name: str, account_type: str = "credit") -> Bank:
    b = Bank(
        name=name,
        account_type=account_type,
        card_digits="1234|5678" if account_type == "credit" else None,
        user_id=1,
    )
    return b


def test_sender_substring_of_bank_name_matches():
    banks = [_bank("EBL Credit Card")]
    assert match_bank_by_sender(banks, "EBL") is banks[0]


def test_bank_name_substring_of_sender_matches():
    banks = [_bank("EBL")]
    assert match_bank_by_sender(banks, "EBL Alert") is banks[0]


def test_matching_is_case_insensitive():
    banks = [_bank("EBL Credit Card")]
    assert match_bank_by_sender(banks, "ebl") is banks[0]


def test_deposit_banks_are_ignored():
    banks = [_bank("EBL", account_type="deposit")]
    assert match_bank_by_sender(banks, "EBL") is None


def test_longest_name_wins_on_multi_match():
    short = _bank("EBL")
    long = _bank("EBL Credit Card")
    assert match_bank_by_sender([short, long], "EBL Credit Card monthly") is long


def test_true_length_tie_returns_none():
    a = _bank("ABC Card")
    b = _bank("XYZ Card")
    # Sender contains both substrings ("Card") — same length matches, tie -> None.
    assert match_bank_by_sender([a, b], "ABC Card XYZ Card") is None


def test_no_candidates_returns_none():
    assert match_bank_by_sender([_bank("EBL")], "SCB") is None


def test_empty_sender_returns_none():
    assert match_bank_by_sender([_bank("EBL")], "") is None


def test_empty_bank_list_returns_none():
    assert match_bank_by_sender([], "EBL") is None
