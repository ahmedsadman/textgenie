import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../models/finance/summary.dart';
import '../../../state/finance_providers.dart';
import '../../../theme/catppuccin_theme.dart';
import '../../../utils/currency_format.dart';
import '../../../utils/date_range.dart';
import '../../../utils/time_format.dart';
import '../section_header.dart';
import 'date_range_selector.dart';
import 'finance_placeholders.dart';

/// Monthly income-vs-expense area chart with gradient fills, themed to
/// Catppuccin (income = green, expense = red).
class SummaryGraphCard extends ConsumerStatefulWidget {
  const SummaryGraphCard({super.key});

  @override
  ConsumerState<SummaryGraphCard> createState() => _SummaryGraphCardState();
}

class _SummaryGraphCardState extends ConsumerState<SummaryGraphCard> {
  DateRangePreset _preset = DateRangePreset.lastYear;

  @override
  Widget build(BuildContext context) {
    final range = resolveDateRange(_preset);
    final async = ref.watch(summaryProvider(range));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Expanded(child: SectionHeader('Summary')),
            DateRangeSelector(
              value: _preset,
              onSelected: (p) => setState(() => _preset = p),
            ),
          ],
        ),
        SizedBox(
          height: 260,
          child: async.when(
            loading: () => const FinanceLoading(height: 260),
            error: (_, _) => const FinanceError('Could not load the graph.'),
            data: (result) => result.data.isEmpty
                ? const Center(
                    child: EmptyHint('No transactions in selected range.'),
                  )
                : _Chart(summary: result.data),
          ),
        ),
        const SizedBox(height: 8),
        const _Legend(),
      ],
    );
  }
}

class _Chart extends StatelessWidget {
  const _Chart({required this.summary});

  final Summary summary;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final buckets = summary.series;
    final labelEvery = (buckets.length / 6).ceil().clamp(1, buckets.length);

    LineChartBarData bar(List<FlSpot> spots, Color color) => LineChartBarData(
      spots: spots,
      color: color,
      isCurved: true,
      barWidth: 2,
      dotData: const FlDotData(show: false),
      belowBarData: BarAreaData(
        show: true,
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [color.withValues(alpha: 0.4), color.withValues(alpha: 0.0)],
        ),
      ),
    );

    final incomeSpots = <FlSpot>[
      for (var i = 0; i < buckets.length; i++)
        FlSpot(i.toDouble(), buckets[i].incomeValue),
    ];
    final expenseSpots = <FlSpot>[
      for (var i = 0; i < buckets.length; i++)
        FlSpot(i.toDouble(), buckets[i].expenseValue),
    ];

    return LineChart(
      LineChartData(
        minY: 0,
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (_) =>
              FlLine(color: theme.colorScheme.outlineVariant, strokeWidth: 1),
        ),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 44,
              getTitlesWidget: (value, meta) => Text(
                formatCompact(value),
                style: theme.textTheme.labelSmall?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 24,
              getTitlesWidget: (value, meta) {
                final i = value.round();
                if (i < 0 || i >= buckets.length) {
                  return const SizedBox.shrink();
                }
                if (i % labelEvery != 0) return const SizedBox.shrink();
                return Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    monthYearLabel(buckets[i].monthStart),
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: theme.colorScheme.outline,
                    ),
                  ),
                );
              },
            ),
          ),
        ),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipColor: (_) => theme.colorScheme.surfaceContainerHighest,
          ),
        ),
        lineBarsData: [
          bar(incomeSpots, AppTheme.income),
          bar(expenseSpots, AppTheme.expense),
        ],
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _dot(context, AppTheme.income, 'Income'),
        const SizedBox(width: 16),
        _dot(context, AppTheme.expense, 'Expense'),
      ],
    );
  }

  Widget _dot(BuildContext context, Color color, String label) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      ),
      const SizedBox(width: 6),
      Text(label, style: Theme.of(context).textTheme.labelMedium),
    ],
  );
}
