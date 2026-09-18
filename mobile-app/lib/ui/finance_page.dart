import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/finance_providers.dart';
import '../state/providers.dart';
import '../utils/api_config.dart';
import 'widgets/finance/credit_card_bills_section.dart';
import 'widgets/finance/stats_card.dart';
import 'widgets/finance/summary_graph_card.dart';
import 'widgets/finance/total_balance_card.dart';
import 'widgets/finance/transactions_section.dart';

/// The Finance tab: balances, credit-card bills, stats, summary graph and
/// transactions. Read-only, offline-aware (serves cached data with a stale
/// warning), and refreshed app-wide via pull-to-refresh.
class FinancePage extends ConsumerStatefulWidget {
  const FinancePage({super.key});

  @override
  ConsumerState<FinancePage> createState() => _FinancePageState();
}

class _FinancePageState extends ConsumerState<FinancePage> {
  bool _staleToastShown = false;

  void _showStaleToast() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Showing saved data — you appear offline')),
    );
  }

  Future<void> _refresh() async {
    refreshAllFinance(ref);
    // Await one provider so the indicator lingers until data settles; swallow
    // errors so a failed refresh doesn't throw out of the RefreshIndicator.
    try {
      await ref.read(banksProvider.future);
    } catch (_) {
      // Offline with no cache — the sections render their own error state.
    }
  }

  @override
  Widget build(BuildContext context) {
    // Surface a one-off toast whenever cached (stale) data is served.
    ref.listen(banksProvider, (previous, next) {
      final stale = next.value?.stale ?? false;
      if (stale && !_staleToastShown) {
        _staleToastShown = true;
        _showStaleToast();
      } else if (!stale) {
        _staleToastShown = false;
      }
    });

    // When the webhook URL changes, drop the previous account's cache. Skip
    // the initial resolution (no previous) so a cold start never wipes cache.
    ref.listen(settingsControllerProvider, (previous, next) {
      if (previous == null) return;
      if (previous.webhookUrl != next.webhookUrl) {
        ref.read(financeRepositoryProvider).clearCache();
        refreshAllFinance(ref);
      }
    });

    final settings = ref.watch(settingsControllerProvider);
    final config = parseWebhookUrl(settings.webhookUrl);

    return Scaffold(
      appBar: AppBar(title: const Text('Finance')),
      body: config == null
          ? const _ConnectPrompt()
          : RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                padding: const EdgeInsets.all(12),
                children: const [
                  TotalBalanceCard(),
                  SizedBox(height: 8),
                  CreditCardBillsSection(),
                  SizedBox(height: 8),
                  StatsCard(),
                  SizedBox(height: 8),
                  SummaryGraphCard(),
                  SizedBox(height: 8),
                  TransactionsSection(),
                ],
              ),
            ),
    );
  }
}

/// Shown when no webhook URL is configured (nothing to authenticate with).
class _ConnectPrompt extends StatelessWidget {
  const _ConnectPrompt();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.account_balance_wallet_outlined,
              size: 48,
              color: theme.colorScheme.primary,
            ),
            const SizedBox(height: 16),
            Text(
              'Connect to view Finance',
              style: theme.textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Add your webhook URL in Settings to load balances, bills and '
              'transactions on this device.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.outline,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
