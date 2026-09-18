import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/data/finance_repository.dart';
import 'package:textgenie/models/finance/averages.dart';
import 'package:textgenie/state/finance_providers.dart';
import 'package:textgenie/theme/catppuccin_theme.dart';
import 'package:textgenie/ui/widgets/finance/stats_card.dart';

void main() {
  testWidgets('shows formatted averages', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          averagesProvider.overrideWith(
            (ref) async => const CachedResult(
              data: Averages(avgSpend: '1200.00', avgSaving: '800.50'),
              stale: false,
            ),
          ),
          currencyProvider.overrideWith(
            (ref) async => const CachedResult(data: 'BDT', stale: false),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.theme,
          home: const Scaffold(body: StatsCard()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('AVG SPEND/MONTH'), findsOneWidget);
    expect(find.text('1,200.00 BDT'), findsOneWidget);
    expect(find.text('800.50 BDT'), findsOneWidget);
  });

  testWidgets('shows placeholders while loading', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          averagesProvider.overrideWith(
            (ref) => Completer<CachedResult<Averages>>().future,
          ),
          currencyProvider.overrideWith(
            (ref) => Completer<CachedResult<String>>().future,
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.theme,
          home: const Scaffold(body: StatsCard()),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('—'), findsNWidgets(2));
  });
}
