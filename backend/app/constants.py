from typing import Literal

TransactionType = Literal["income", "expense", "transfer"]
INCOME: TransactionType = "income"
EXPENSE: TransactionType = "expense"
TRANSFER: TransactionType = "transfer"
