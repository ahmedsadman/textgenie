import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:textgenie/data/finance_repository.dart';
import 'package:textgenie/data/settings_repository.dart';
import 'package:textgenie/models/finance/bank.dart';
import 'package:textgenie/models/finance/summary.dart';
import 'package:textgenie/models/finance/transactions_page.dart';
import 'package:textgenie/models/finance/trends.dart';
import 'package:textgenie/state/finance_providers.dart';
import 'package:textgenie/state/providers.dart';
import 'package:textgenie/theme/catppuccin_theme.dart';
import 'package:textgenie/ui/finance_page.dart';
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

Trends _trends() => Trends(
  windowMonths: 3,
  sparkMonths: [for (var m = 3; m <= 8; m++) DateTime(2025, m, 1)],
  income: const TrendMetric(
    recentAvg: '100.00',
    priorAvg: '80.00',
    changePct: '25.0',
    direction: TrendDirection.up,
    spark: ['80', '80', '80', '100', '100', '100'],
  ),
  spend: const TrendMetric(
    recentAvg: '50.00',
    priorAvg: '50.00',
    changePct: '0.0',
    direction: TrendDirection.flat,
    spark: ['50', '50', '50', '50', '50', '50'],
  ),
  savingsRate: const SavingsRateTrend(
    recent: '0.5',
    prior: '0.4',
    changePp: '10.0',
    direction: TrendDirection.up,
    spark: ['0.4', '0.4', '0.4', '0.5', '0.5', '0.5'],
  ),
);

Future<void> _pump(
  WidgetTester tester, {
  String? webhookUrl = 'https://host/api/webhook/tok',
  bool stale = false,
}) async {
  // A tall surface so every section is laid out within the viewport.
  tester.view.physicalSize = const Size(1200, 4000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        settingsRepositoryProvider.overrideWithValue(SettingsRepository(prefs)),
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
        trendsProvider.overrideWith(
          (ref) async => CachedResult(data: _trends(), stale: stale),
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
    expect(find.byType(SummaryGraphCard), findsOneWidget);
    expect(find.byType(TransactionsSection), findsOneWidget);

    // Trend metrics render in their own Trends card.
    expect(find.text('Income / Month'), findsOneWidget);
    expect(find.text('Spend / Month'), findsOneWidget);
    expect(find.text('Savings Rate'), findsOneWidget);

    final totalY = tester.getTopLeft(find.byType(TotalBalanceCard)).dy;
    final summaryY = tester.getTopLeft(find.byType(SummaryGraphCard)).dy;
    final txY = tester.getTopLeft(find.byType(TransactionsSection)).dy;
    expect(totalY, lessThan(summaryY));
    expect(summaryY, lessThan(txY));
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
