import 'package:flutter/material.dart';

import '../../../models/finance/bank.dart';
import '../../../theme/catppuccin_theme.dart';
import '../../../utils/currency_format.dart';
import '../../../utils/time_format.dart';
import 'finance_badge.dart';

/// Per-bank breakdown revealed under the total-balance card. Deposit accounts
/// show their balance; credit cards show their masked number and are excluded
/// from the total.
class BankBreakdownList extends StatelessWidget {
  const BankBreakdownList({
    required this.banks,
    required this.currency,
    super.key,
  });

  final List<Bank> banks;
  final String currency;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (banks.isEmpty) {
      return Padding(
        padding: const EdgeInsets.only(top: 12),
        child: Text(
          'No accounts yet.',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.outline,
          ),
        ),
      );
    }

    return Column(
      children: [
        const Divider(height: 24),
        for (final bank in banks) _BankRow(bank: bank, currency: currency),
      ],
    );
  }
}

class _BankRow extends StatelessWidget {
  const _BankRow({required this.bank, required this.currency});

  final Bank bank;
  final String currency;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        bank.name,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (bank.isCredit) ...[
                      const SizedBox(width: 8),
                      FinanceBadge('Credit', color: AppTheme.flavor.peach),
                    ],
                  ],
                ),
                if (bank.isCredit)
                  Text(
                    '•••• ${bank.last4 ?? '----'} · not counted',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.outline,
                    ),
                  )
                else if (bank.lastBalanceAt != null)
                  Text(
                    'Updated ${relativeTime(bank.lastBalanceAt!.toLocal())}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.outline,
                    ),
                  ),
              ],
            ),
          ),
          if (bank.isDeposit)
            Text(
              bank.lastBalance != null
                  ? formatAmount(bank.lastBalance, currency)
                  : 'No balance yet',
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
        ],
      ),
    );
  }
}
