import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/data/finance_repository.dart';
import 'package:textgenie/models/finance/bank.dart';
import 'package:textgenie/state/finance_providers.dart';
import 'package:textgenie/theme/catppuccin_theme.dart';
import 'package:textgenie/ui/widgets/finance/total_balance_card.dart';

import 'support/balance_test_overrides.dart';

Bank _deposit(String name, String? balance) => Bank(
  id: name.hashCode,
  name: name,
  accountType: 'deposit',
  lastBalance: balance,
  lastBalanceAt: DateTime(2025, 1, 1),
  createdAt: DateTime(2025, 1, 1),
);

Bank _credit(String name) => Bank(
  id: name.hashCode,
  name: name,
  accountType: 'credit',
  cardDigits: '1234|5678',
  createdAt: DateTime(2025, 1, 1),
);

Future<void> _pump(
  WidgetTester tester,
  List<Bank> banks, {
  bool hidden = false,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        overrideBalanceHidden(hidden),
        banksProvider.overrideWith(
          (ref) async => CachedResult(data: banks, stale: false),
        ),
        currencyProvider.overrideWith(
          (ref) async => const CachedResult(data: 'BDT', stale: false),
        ),
      ],
      child: MaterialApp(
        theme: AppTheme.theme,
        home: const Scaffold(body: TotalBalanceCard()),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('sums deposit balances and hides the breakdown by default', (
    tester,
  ) async {
    await _pump(tester, [
      _deposit('Checking', '1000.00'),
      _deposit('Savings', '500.50'),
      _credit('Visa'),
    ]);

    expect(find.text('Total Balance'), findsOneWidget);
    expect(find.text('1,500.50 BDT'), findsOneWidget);
    // Breakdown is collapsed initially.
    expect(find.text('Checking'), findsNothing);
  });

  testWidgets('tapping toggles the per-bank breakdown', (tester) async {
    await _pump(tester, [_deposit('Checking', '1000.00'), _credit('Visa')]);

    await tester.tap(find.text('Total Balance'));
    await tester.pumpAndSettle();

    expect(find.text('Checking'), findsOneWidget);
    // Credit card is shown but excluded from the total.
    expect(find.text('Visa'), findsOneWidget);
    expect(find.textContaining('not counted'), findsOneWidget);

    await tester.tap(find.text('Total Balance'));
    await tester.pumpAndSettle();
    expect(find.text('Checking'), findsNothing);
  });

  testWidgets('shows a placeholder when there are no banks', (tester) async {
    await _pump(tester, const []);
    expect(find.text('—'), findsOneWidget);
  });

  testWidgets('shows the latest update time in both collapsed and expanded '
      'states', (tester) async {
    await _pump(tester, [_deposit('Checking', '1000.00')]);

    // Collapsed: only the top-level "Updated …" subtitle is visible.
    expect(find.textContaining('Updated '), findsOneWidget);

    await tester.tap(find.text('Total Balance'));
    await tester.pumpAndSettle();

    // Expanded: the top-level subtitle plus the bank row's own subline.
    expect(find.textContaining('Updated '), findsNWidgets(2));
  });

  testWidgets('omits the update subtitle when no deposit has a timestamp', (
    tester,
  ) async {
    await _pump(tester, [_credit('Visa')]);
    expect(find.textContaining('Updated '), findsNothing);
  });

  testWidgets('masks the total when balances are hidden', (tester) async {
    await _pump(tester, [_deposit('Checking', '1000.00')], hidden: true);

    expect(find.text('1,000.00 BDT'), findsNothing);
    // The total balance is masked (currency kept). Trends moved to their own card.
    expect(find.text('**** BDT'), findsOneWidget);
  });
}
