import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../models/finance/bank.dart';
import '../../../state/finance_providers.dart';
import '../../../state/providers.dart';
import '../../../utils/currency_format.dart';
import 'bank_breakdown_list.dart';

/// A single averages stat: an uppercase caption above a value. The value is
/// deliberately smaller than the total balance so the balance stays dominant.
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
        const SizedBox(height: 2),
        Text(
          value,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}

/// Total deposit balance across accounts. Tapping toggles a per-bank breakdown
/// (hidden by default).
class TotalBalanceCard extends ConsumerStatefulWidget {
  const TotalBalanceCard({super.key});

  @override
  ConsumerState<TotalBalanceCard> createState() => _TotalBalanceCardState();
}

class _TotalBalanceCardState extends ConsumerState<TotalBalanceCard> {
  bool _expanded = false;

  static double _total(List<Bank> banks) => banks
      .where((b) => b.isDeposit && b.lastBalance != null)
      .fold(0.0, (sum, b) => sum + (double.tryParse(b.lastBalance!) ?? 0));

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final banks = ref.watch(banksProvider).value?.data;
    final currency = ref.watch(currencyProvider).value?.data ?? '';
    final averages = ref.watch(averagesProvider).value?.data;
    final hidden = ref.watch(balanceHiddenProvider);

    final hasBanks = banks != null && banks.isNotEmpty;
    final totalLabel = hasBanks
        ? formatMoney(_total(banks), currency, hidden: hidden)
        : '—';

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: hasBanks ? () => setState(() => _expanded = !_expanded) : null,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Total Balance',
                          style: theme.textTheme.labelMedium?.copyWith(
                            color: theme.colorScheme.outline,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          totalLabel,
                          style: theme.textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (hasBanks)
                    AnimatedRotation(
                      turns: _expanded ? 0.5 : 0,
                      duration: const Duration(milliseconds: 200),
                      child: Icon(
                        Icons.expand_more,
                        color: theme.colorScheme.outline,
                      ),
                    ),
                ],
              ),
              if (_expanded && hasBanks)
                BankBreakdownList(
                  banks: banks,
                  currency: currency,
                  hidden: hidden,
                ),
              const Divider(height: 24),
              _Stat(
                label: 'Avg Spend/Month',
                value: averages == null
                    ? '—'
                    : formatAmount(averages.avgSpend, currency, hidden: hidden),
              ),
              const SizedBox(height: 12),
              _Stat(
                label: 'Avg Saving/Month',
                value: averages == null
                    ? '—'
                    : formatAmount(
                        averages.avgSaving,
                        currency,
                        hidden: hidden,
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
