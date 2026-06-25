from decimal import Decimal

from app.models import Bank, BankSender, BankTemplate
from app.services.template_parser import extract_bank_data, normalize, template_to_regex

# --- normalize ---


def test_normalize_removes_commas():
    assert normalize("1,72,454.00") == "172454.00"


def test_normalize_replaces_newlines():
    assert normalize("hello\nworld") == "hello world"


def test_normalize_collapses_whitespace():
    assert normalize("hello   world") == "hello world"


def test_normalize_strips():
    assert normalize("  hello  ") == "hello"


def test_normalize_combined():
    text = "TK 1,72,454.00 has been\ncredited to your A/C.  Balance: TK 11,14,024.81"
    expected = "TK 172454.00 has been credited to your A/C. Balance: TK 1114024.81"
    assert normalize(text) == expected


# --- template_to_regex ---


def test_template_to_regex_matches_balance():
    pattern = template_to_regex("Your balance is TK {{balance}}.")
    m = pattern.search("Your balance is TK 1500.50.")
    assert m is not None
    assert m.group(1) == "1500.50"


def test_template_to_regex_matches_integer_balance():
    pattern = template_to_regex("Balance: {{balance}} BDT")
    m = pattern.search("Balance: 2000 BDT")
    assert m is not None
    assert m.group(1) == "2000"


def test_template_to_regex_escapes_special_chars():
    pattern = template_to_regex("A/C# 10726**0001. Balance: {{balance}}")
    m = pattern.search("A/C# 10726**0001. Balance: 5000.00")
    assert m is not None
    assert m.group(1) == "5000.00"


def test_template_to_regex_no_match():
    pattern = template_to_regex("Balance: {{balance}} BDT")
    m = pattern.search("Your ticket is confirmed")
    assert m is None


# --- extract_bank_data ---


def _make_bank(name, senders, templates):
    bank = Bank(name=name, user_id=1)
    bank.senders = [BankSender(name=s) for s in senders]
    bank.templates = [BankTemplate(template=normalize(t)) for t in templates]
    return bank


def test_extract_matches_sender_and_template():
    bank = _make_bank(
        "BRAC Bank",
        ["BRACBANK"],
        ["TK {{balance}} is your current balance"],
    )
    sms = "TK 1,500.00 is your current balance"
    result = extract_bank_data("BRACBANK", sms, [bank])
    assert result is not None
    matched_bank, balance = result
    assert matched_bank is bank
    assert balance == Decimal("1500.00")


def test_extract_sender_case_insensitive():
    bank = _make_bank("BRAC Bank", ["BRACBANK"], ["Balance: {{balance}}"])
    result = extract_bank_data("bracbank", "Balance: 2000", [bank])
    assert result is not None
    assert result[1] == Decimal("2000")


def test_extract_no_sender_match():
    bank = _make_bank("BRAC Bank", ["BRACBANK"], ["Balance: {{balance}}"])
    result = extract_bank_data("UNKNOWN", "Balance: 2000", [bank])
    assert result is None


def test_extract_no_template_match():
    bank = _make_bank("BRAC Bank", ["BRACBANK"], ["Balance: {{balance}} BDT"])
    result = extract_bank_data("BRACBANK", "Your ticket is confirmed", [bank])
    assert result is None


def test_extract_multiple_templates_first_match_wins():
    bank = _make_bank(
        "BRAC Bank",
        ["BRACBANK"],
        [
            "Credited. Balance: {{balance}} BDT",
            "Debited. Balance: {{balance}} BDT",
        ],
    )
    result = extract_bank_data("BRACBANK", "Debited. Balance: 500 BDT", [bank])
    assert result is not None
    assert result[1] == Decimal("500")


def test_extract_multiple_banks_correct_one_matched():
    brac = _make_bank("BRAC", ["BRACBANK"], ["Balance: {{balance}}"])
    ebl = _make_bank("EBL", ["EBLBANK"], ["Your balance: {{balance}}"])
    result = extract_bank_data("EBLBANK", "Your balance: 3000", [brac, ebl])
    assert result is not None
    assert result[0].name == "EBL"
    assert result[1] == Decimal("3000")


def test_extract_real_sms_balance_only():
    bank = _make_bank(
        "BRAC Bank",
        ["BRACBANK"],
        ["Your A/C balance is TK {{balance}}. For Enquiry call: 16221"],
    )
    sms = (
        "TK 1,72,454.00 has been credited to your A/C# 10726**0001"
        " on 24-06-26. Your A/C balance is TK 11,14,024.81."
        " For Enquiry call: 16221"
    )
    result = extract_bank_data("BRACBANK", sms, [bank])
    assert result is not None
    assert result[1] == Decimal("1114024.81")
