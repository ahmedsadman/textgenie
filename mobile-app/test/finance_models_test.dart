import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/models/finance/averages.dart';
import 'package:textgenie/models/finance/bank.dart';
import 'package:textgenie/models/finance/bill.dart';
import 'package:textgenie/models/finance/sms_message.dart';
import 'package:textgenie/models/finance/summary.dart';
import 'package:textgenie/models/finance/transaction.dart';
import 'package:textgenie/models/finance/transactions_page.dart';

void main() {
  test('Bank parses a deposit account', () {
    final bank = Bank.fromJson({
      'id': 1,
      'name': 'Checking',
      'account_type': 'deposit',
      'card_digits': null,
      'last_balance': '1500.00',
      'last_balance_at': '2025-01-02T03:04:05Z',
      'created_at': '2025-01-01T00:00:00Z',
    });
    expect(bank.isDeposit, isTrue);
    expect(bank.isCredit, isFalse);
    expect(bank.lastBalance, '1500.00');
    expect(bank.last4, isNull);
  });

  test('Bank parses a credit card and extracts last4', () {
    final bank = Bank.fromJson({
      'id': 2,
      'name': 'Visa',
      'account_type': 'credit',
      'card_digits': '1234|5678',
      'last_balance': null,
      'last_balance_at': null,
      'created_at': '2025-01-01T00:00:00Z',
    });
    expect(bank.isCredit, isTrue);
    expect(bank.last4, '5678');
    expect(bank.lastBalance, isNull);
  });

  test('TransactionItem parses with nullable fields and numeric amounts', () {
    final tx = TransactionItem.fromJson({
      'id': 10,
      'message_id': 99,
      'bank_id': null,
      'bank_name': null,
      'bank_account_type': null,
      'sender': 'ACME',
      'normalized_amount': 250.75, // number, not string
      'normalized_currency': 'BDT',
      'original_amount': null,
      'original_currency': null,
      'type': 'expense',
      'date': '2025-01-05T12:00:00Z',
      'paired_with_id': null,
      'paired_with_message_id': null,
      'bill_id': null,
    });
    expect(tx.type, TxType.expense);
    expect(tx.normalizedAmount, '250.75');
    expect(tx.amountValue, 250.75);
    expect(tx.date, DateTime.utc(2025, 1, 5, 12));
  });

  test('TransactionsPage parses totals and computes total pages', () {
    final page = TransactionsPage.fromJson({
      'transactions': [],
      'total': 25,
      'page': 1,
      'page_size': 10,
      'totals': {'income': '100.00', 'expense': '40.00'},
    });
    expect(page.totals.income, '100.00');
    expect(page.totalPages, 3);
  });

  test('Bill parses paid/unpaid and linked ids', () {
    final paid = Bill.fromJson({
      'id': 1,
      'message_id': 2,
      'sender': 'BANK',
      'received_at': '2025-01-10T00:00:00Z',
      'bank_id': 5,
      'bank_name': 'Visa',
      'normalized_total_due': '500.00',
      'normalized_currency': 'BDT',
      'statement_period': '2025-01-01',
      'paid_at': '2025-01-15T00:00:00Z',
      'linked_transaction_ids': [7, 8],
      'created_at': '2025-01-10T00:00:00Z',
    });
    expect(paid.isPaid, isTrue);
    expect(paid.linkedTransactionIds, [7, 8]);
    // Date-only string parses to local midnight (no timezone marker).
    expect(paid.statementPeriod, DateTime(2025, 1, 1));

    final unpaid = Bill.fromJson({
      'id': 2,
      'message_id': 3,
      'sender': 'BANK',
      'received_at': '2025-02-10T00:00:00Z',
      'bank_id': null,
      'bank_name': null,
      'normalized_total_due': '10.00',
      'normalized_currency': 'BDT',
      'created_at': '2025-02-10T00:00:00Z',
    });
    expect(unpaid.isPaid, isFalse);
    expect(unpaid.linkedTransactionIds, isEmpty);
    expect(unpaid.statementPeriod, isNull);
  });

  test('Summary parses its series', () {
    final summary = Summary.fromJson({
      'series': [
        {'month_start': '2025-01-01', 'income': '100.00', 'expense': '30.00'},
      ],
    });
    expect(summary.isEmpty, isFalse);
    expect(summary.series.single.incomeValue, 100.0);
    expect(summary.series.single.expenseValue, 30.0);
  });

  test('Averages parses fields', () {
    final avg = Averages.fromJson({
      'avg_spend': '30.00',
      'avg_saving': '70.00',
    });
    expect(avg.avgSpend, '30.00');
    expect(avg.avgSaving, '70.00');
  });

  test('ApiMessage parses fields', () {
    final message = ApiMessage.fromJson({
      'id': 4,
      'sender': 'ACME',
      'content': 'Your bill is due',
      'received_at': '2025-01-01T00:00:00Z',
    });
    expect(message.content, 'Your bill is due');
    expect(message.sender, 'ACME');
  });
}
