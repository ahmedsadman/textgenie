from typing import Literal

TransactionType = Literal["income", "expense", "transfer"]
INCOME: TransactionType = "income"
EXPENSE: TransactionType = "expense"
TRANSFER: TransactionType = "transfer"

AccountType = Literal["deposit", "credit"]
DEPOSIT: AccountType = "deposit"
CREDIT: AccountType = "credit"

Currency = Literal["BDT", "USD", "EUR"]
BDT: Currency = "BDT"
USD: Currency = "USD"
EUR: Currency = "EUR"
DEFAULT_CURRENCY: Currency = BDT
