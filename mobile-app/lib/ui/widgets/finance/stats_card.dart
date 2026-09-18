import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../state/finance_providers.dart';
import '../../../utils/currency_format.dart';

/// All-time monthly averages: average spend and average saving.
class StatsCard extends ConsumerWidget {
  const StatsCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final averages = ref.watch(averagesProvider).value?.data;
    final currency = ref.watch(currencyProvider).value?.data ?? '';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Expanded(
              child: _Stat(
                label: 'Avg Spend/Month',
                value: averages == null
                    ? '—'
                    : formatAmount(averages.avgSpend, currency),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _Stat(
                label: 'Avg Saving/Month',
                value: averages == null
                    ? '—'
                    : formatAmount(averages.avgSaving, currency),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label.toUpperCase(),
          style: theme.textTheme.labelSmall?.copyWith(
            color: theme.colorScheme.outline,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          value,
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}
