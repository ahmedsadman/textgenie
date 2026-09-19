import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/finance_providers.dart';
import '../state/providers.dart';
import '../utils/api_config.dart';
import 'widgets/connect_prompt.dart';
import 'widgets/finance/credit_card_bills_section.dart';
import 'widgets/finance/summary_graph_card.dart';
import 'widgets/finance/total_balance_card.dart';
import 'widgets/finance/transactions_section.dart';
import 'widgets/finance/trends_card.dart';

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
    final hidden = ref.watch(balanceHiddenProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Finance'),
        actions: [
          if (config != null)
            IconButton(
              tooltip: hidden ? 'Show balances' : 'Hide balances',
              icon: Icon(hidden ? Icons.visibility_off : Icons.visibility),
              onPressed: () =>
                  ref.read(balanceHiddenProvider.notifier).toggle(),
            ),
        ],
      ),
      body: config == null
          ? const ConnectPrompt(
              icon: Icons.account_balance_wallet_outlined,
              title: 'Connect to view Finance',
              message:
                  'Add your webhook URL in Settings to load balances, bills '
                  'and transactions on this device.',
            )
          : RefreshIndicator(
              onRefresh: _refresh,
              // A non-lazy Column (not a ListView) keeps every top card mounted
              // so their autoDispose providers stay subscribed. Otherwise
              // scrolling a card off-screen disposes it and refetches on return
              // (and paginating transactions, which pushes the cards off-screen,
              // does the same). Content is bounded (10 tx/page) so eager build
              // is fine. AlwaysScrollable keeps pull-to-refresh working when the
              // content is short.
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(12),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TotalBalanceCard(),
                    SizedBox(height: 8),
                    TrendsCard(),
                    SizedBox(height: 8),
                    CreditCardBillsSection(),
                    SizedBox(height: 8),
                    SummaryGraphCard(),
                    SizedBox(height: 8),
                    TransactionsSection(),
                  ],
                ),
              ),
            ),
    );
  }
}
