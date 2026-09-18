import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/finance_cache.dart';
import '../data/finance_repository.dart';
import '../models/finance/averages.dart';
import '../models/finance/bank.dart';
import '../models/finance/bills_page.dart';
import '../models/finance/sms_message.dart';
import '../models/finance/summary.dart';
import '../models/finance/transactions_page.dart';
import '../models/finance/tx_query.dart';
import '../services/api_client.dart';
import '../utils/date_range.dart';
import 'providers.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  // Reuse the app-wide connectivity service (DRY).
  final client = ApiClient(
    connectivity: ref.watch(appServicesProvider).connectivity,
  );
  ref.onDispose(client.close);
  return client;
});

final financeCacheProvider = Provider<FinanceCache>(
  (ref) => FinanceCache(ref.watch(databaseProvider)),
);

final financeRepositoryProvider = Provider<FinanceRepository>(
  (ref) => FinanceRepository(
    api: ref.watch(apiClientProvider),
    cache: ref.watch(financeCacheProvider),
    settings: ref.watch(settingsRepositoryProvider),
  ),
);

final banksProvider = FutureProvider.autoDispose<CachedResult<List<Bank>>>(
  (ref) => ref.watch(financeRepositoryProvider).banks(),
);

final currencyProvider = FutureProvider.autoDispose<CachedResult<String>>(
  (ref) => ref.watch(financeRepositoryProvider).currency(),
);

final averagesProvider = FutureProvider.autoDispose<CachedResult<Averages>>(
  (ref) => ref.watch(financeRepositoryProvider).averages(),
);

final summaryProvider = FutureProvider.autoDispose
    .family<CachedResult<Summary>, DateRange>(
      (ref, range) => ref.watch(financeRepositoryProvider).summary(range),
    );

final transactionsProvider = FutureProvider.autoDispose
    .family<CachedResult<TransactionsPage>, TxQuery>(
      (ref, query) => ref.watch(financeRepositoryProvider).transactions(query),
    );

final billsProvider = FutureProvider.autoDispose
    .family<CachedResult<BillsPage>, int>(
      (ref, bankId) => ref.watch(financeRepositoryProvider).bills(bankId),
    );

final messageProvider = FutureProvider.autoDispose
    .family<CachedResult<ApiMessage>, int>(
      (ref, id) => ref.watch(financeRepositoryProvider).message(id),
    );

/// Invalidates every finance provider so a pull-to-refresh reloads all data
/// app-wide. Calling `invalidate` on a family (no argument) clears all its
/// instances.
void refreshAllFinance(WidgetRef ref) {
  ref.invalidate(banksProvider);
  ref.invalidate(currencyProvider);
  ref.invalidate(averagesProvider);
  ref.invalidate(summaryProvider);
  ref.invalidate(transactionsProvider);
  ref.invalidate(billsProvider);
  ref.invalidate(messageProvider);
}
