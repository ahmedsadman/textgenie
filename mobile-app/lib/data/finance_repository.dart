import 'dart:convert';

import '../models/finance/averages.dart';
import '../models/finance/bank.dart';
import '../models/finance/bills_page.dart';
import '../models/finance/sms_message.dart';
import '../models/finance/summary.dart';
import '../models/finance/transactions_page.dart';
import '../models/finance/tx_query.dart';
import '../services/api_client.dart';
import '../utils/api_config.dart';
import '../utils/date_range.dart';
import 'finance_cache.dart';
import 'settings_repository.dart';

/// The outcome of a finance read: the parsed [data] plus whether it was served
/// from cache because the live fetch failed ([stale]).
class CachedResult<T> {
  const CachedResult({required this.data, required this.stale, this.fetchedAt});

  final T data;
  final bool stale;
  final DateTime? fetchedAt;
}

/// Reads finance data from the backend with a read-through sqflite cache.
///
/// On a successful fetch the response is cached and returned as fresh. On any
/// [ApiException] the last cached response is returned as stale; if nothing is
/// cached the error propagates. When no webhook URL is configured the caller
/// gets [ApiException.unauthorized] (drives the "connect in Settings" state).
class FinanceRepository {
  FinanceRepository({
    required this._api,
    required this._cache,
    required this._settings,
    int Function()? nowMs,
  }) : _nowMs = nowMs ?? (() => DateTime.now().millisecondsSinceEpoch);

  final ApiClient _api;
  final FinanceCache _cache;
  final SettingsRepository _settings;
  final int Function() _nowMs;

  ApiConfig _requireConfig() {
    final config = parseWebhookUrl(_settings.webhookUrl);
    if (config == null) {
      throw ApiException.unauthorized('No webhook URL configured');
    }
    return config;
  }

  Future<CachedResult<T>> _fetch<T>(
    String path,
    Map<String, dynamic>? query,
    T Function(Object? json) parse,
  ) async {
    final config = _requireConfig();
    final key = financeCacheKey(path, query);
    try {
      final json = await _api.get(config, path, query: query);
      await _cache.write(key, jsonEncode(json), _nowMs());
      return CachedResult(
        data: parse(json),
        stale: false,
        fetchedAt: DateTime.fromMillisecondsSinceEpoch(_nowMs()),
      );
    } on ApiException {
      final cached = await _cache.read(key);
      if (cached != null) {
        return CachedResult(
          data: parse(jsonDecode(cached.payload)),
          stale: true,
          fetchedAt: DateTime.fromMillisecondsSinceEpoch(cached.fetchedAt),
        );
      }
      rethrow;
    }
  }

  Future<CachedResult<List<Bank>>> banks() => _fetch(
    '/banks',
    null,
    (json) => (json as List)
        .map((e) => Bank.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  Future<CachedResult<String>> currency() => _fetch(
    '/settings/currency',
    null,
    (json) => (json as Map)['currency'] as String,
  );

  Future<CachedResult<Averages>> averages() => _fetch(
    '/transactions/averages',
    null,
    (json) => Averages.fromJson(json as Map<String, dynamic>),
  );

  Future<CachedResult<Summary>> summary(DateRange range) {
    final query = <String, dynamic>{
      if (range.from != null)
        'from_date': range.from!.toUtc().toIso8601String(),
      if (range.to != null) 'to_date': range.to!.toUtc().toIso8601String(),
    };
    return _fetch(
      '/transactions/summary',
      query.isEmpty ? null : query,
      (json) => Summary.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<CachedResult<TransactionsPage>> transactions(TxQuery query) => _fetch(
    '/transactions',
    query.toParams(),
    (json) => TransactionsPage.fromJson(json as Map<String, dynamic>),
  );

  Future<CachedResult<BillsPage>> bills(
    int bankId, {
    int page = 1,
    int pageSize = 20,
  }) => _fetch('/bills', {
    'bank_id': bankId,
    'page': page,
    'page_size': pageSize,
  }, (json) => BillsPage.fromJson(json as Map<String, dynamic>));

  Future<CachedResult<ApiMessage>> message(int id) => _fetch(
    '/messages/$id',
    null,
    (json) => ApiMessage.fromJson(json as Map<String, dynamic>),
  );

  /// Drops all cached finance responses (e.g. when the account/URL changes).
  Future<void> clearCache() => _cache.clearAll();
}
