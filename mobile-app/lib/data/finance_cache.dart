import 'package:sqflite/sqflite.dart';

import 'database.dart';

/// A cached finance API response.
class CachedEntry {
  const CachedEntry({required this.payload, required this.fetchedAt});

  /// The raw JSON body, exactly as returned by the API.
  final String payload;

  /// Epoch milliseconds when this entry was written.
  final int fetchedAt;
}

/// Read/write access to the `finance_cache` blob table. Backs offline support:
/// the last successful response per request is stored and served when the
/// network is unavailable.
class FinanceCache {
  const FinanceCache(this._db);

  final Database _db;

  Future<void> write(String key, String payload, int fetchedAt) async {
    await _db.insert(AppDatabase.financeCacheTable, {
      'cache_key': key,
      'payload': payload,
      'fetched_at': fetchedAt,
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<CachedEntry?> read(String key) async {
    final rows = await _db.query(
      AppDatabase.financeCacheTable,
      where: 'cache_key = ?',
      whereArgs: [key],
      limit: 1,
    );
    if (rows.isEmpty) return null;
    final row = rows.first;
    return CachedEntry(
      payload: row['payload'] as String,
      fetchedAt: row['fetched_at'] as int,
    );
  }

  Future<void> clearAll() async {
    await _db.delete(AppDatabase.financeCacheTable);
  }
}

/// Builds a stable cache key from a request path and its query params. Query
/// keys are sorted so equal requests always map to the same key.
String financeCacheKey(String path, [Map<String, dynamic>? query]) {
  if (query == null || query.isEmpty) return path;
  final keys = query.keys.toList()..sort();
  final parts = <String>[];
  for (final key in keys) {
    final value = query[key];
    if (value == null) continue;
    if (value is Iterable) {
      parts.add('$key=${value.map((e) => e.toString()).join(',')}');
    } else {
      parts.add('$key=$value');
    }
  }
  return parts.isEmpty ? path : '$path?${parts.join('&')}';
}
