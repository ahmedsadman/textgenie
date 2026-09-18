import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/data/finance_repository.dart';
import 'package:textgenie/models/finance/summary.dart';
import 'package:textgenie/state/finance_providers.dart';
import 'package:textgenie/theme/catppuccin_theme.dart';
import 'package:textgenie/ui/widgets/finance/summary_graph_card.dart';

Future<void> _pump(WidgetTester tester, Summary summary) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        summaryProvider.overrideWith(
          (ref, arg) async => CachedResult(data: summary, stale: false),
        ),
      ],
      child: MaterialApp(
        theme: AppTheme.theme,
        home: const Scaffold(body: SummaryGraphCard()),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('renders a line chart with a legend when data exists', (
    tester,
  ) async {
    await _pump(
      tester,
      Summary(
        series: [
          SummaryBucket(
            monthStart: DateTime(2025, 1, 1),
            income: '100',
            expense: '40',
          ),
          SummaryBucket(
            monthStart: DateTime(2025, 2, 1),
            income: '120',
            expense: '90',
          ),
        ],
      ),
    );

    expect(find.byType(LineChart), findsOneWidget);
    expect(find.text('Income'), findsOneWidget);
    expect(find.text('Expense'), findsOneWidget);
  });

  testWidgets('shows an empty message when there is no data', (tester) async {
    await _pump(tester, const Summary(series: []));

    expect(find.byType(LineChart), findsNothing);
    expect(find.text('No transactions in selected range.'), findsOneWidget);
  });
}
