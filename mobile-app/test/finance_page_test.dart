import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/data/finance_repository.dart';
import 'package:textgenie/models/finance/averages.dart';
import 'package:textgenie/models/finance/bank.dart';
import 'package:textgenie/models/finance/summary.dart';
import 'package:textgenie/models/finance/transactions_page.dart';
import 'package:textgenie/state/finance_providers.dart';
import 'package:textgenie/state/providers.dart';
import 'package:textgenie/theme/catppuccin_theme.dart';
import 'package:textgenie/ui/finance_page.dart';
import 'package:textgenie/ui/widgets/finance/stats_card.dart';
import 'package:textgenie/ui/widgets/finance/summary_graph_card.dart';
import 'package:textgenie/ui/widgets/finance/total_balance_card.dart';
import 'package:textgenie/ui/widgets/finance/transactions_section.dart';

class _StubSettings extends SettingsController {
  _StubSettings(this._state);
  final SettingsState _state;
  @override
  SettingsState build() => _state;
}

Bank _deposit() => Bank(
  id: 1,
  name: 'Checking',
  accountType: 'deposit',
  lastBalance: '100.00',
  createdAt: DateTime(2025, 1, 1),
);

TransactionsPage _emptyTx() => const TransactionsPage(
  transactions: [],
  total: 0,
  page: 1,
  pageSize: 10,
  totals: Totals(income: '0', expense: '0'),
);

Future<void> _pump(
  WidgetTester tester, {
  String? webhookUrl = 'https://host/api/webhook/tok',
  bool stale = false,
}) async {
  // A tall surface so every section lays out (the ListView is otherwise lazy).
  tester.view.physicalSize = const Size(1200, 4000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        settingsControllerProvider.overrideWith(
          () => _StubSettings(
            SettingsState(webhookUrl: webhookUrl, resolveContacts: true),
          ),
        ),
        banksProvider.overrideWith(
          (ref) async => CachedResult(data: [_deposit()], stale: stale),
        ),
        currencyProvider.overrideWith(
          (ref) async => CachedResult(data: 'BDT', stale: stale),
        ),
        averagesProvider.overrideWith(
          (ref) async => CachedResult(
            data: const Averages(avgSpend: '10', avgSaving: '5'),
            stale: stale,
          ),
        ),
        summaryProvider.overrideWith(
          (ref, arg) async => CachedResult(
            data: const Summary(series: []),
            stale: stale,
          ),
        ),
        transactionsProvider.overrideWith(
          (ref, arg) async => CachedResult(data: _emptyTx(), stale: stale),
        ),
      ],
      child: MaterialApp(theme: AppTheme.theme, home: const FinancePage()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('renders all sections in order when connected', (tester) async {
    await _pump(tester);

    expect(find.text('Finance'), findsOneWidget); // app bar
    expect(find.byType(TotalBalanceCard), findsOneWidget);
    expect(find.byType(StatsCard), findsOneWidget);
    expect(find.byType(SummaryGraphCard), findsOneWidget);
    expect(find.byType(TransactionsSection), findsOneWidget);

    final totalY = tester.getTopLeft(find.byType(TotalBalanceCard)).dy;
    final statsY = tester.getTopLeft(find.byType(StatsCard)).dy;
    final txY = tester.getTopLeft(find.byType(TransactionsSection)).dy;
    expect(totalY, lessThan(statsY));
    expect(statsY, lessThan(txY));
  });

  testWidgets('shows a connect prompt when no webhook is configured', (
    tester,
  ) async {
    await _pump(tester, webhookUrl: null);

    expect(find.text('Connect to view Finance'), findsOneWidget);
    expect(find.byType(TotalBalanceCard), findsNothing);
  });

  testWidgets('shows a stale-data toast when serving cached data', (
    tester,
  ) async {
    await _pump(tester, stale: true);

    expect(find.textContaining('Showing saved data'), findsOneWidget);
  });

  testWidgets('does not toast when data is fresh', (tester) async {
    await _pump(tester);
    expect(find.textContaining('Showing saved data'), findsNothing);
  });
}
