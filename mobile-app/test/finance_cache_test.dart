import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:textgenie/data/database.dart';
import 'package:textgenie/data/finance_cache.dart';

void main() {
  late Database db;
  late FinanceCache cache;

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  setUp(() async {
    db = await databaseFactory.openDatabase(
      inMemoryDatabasePath,
      options: OpenDatabaseOptions(
        version: 3,
        onCreate: AppDatabase.createSchema,
        onUpgrade: AppDatabase.onUpgrade,
      ),
    );
    cache = FinanceCache(db);
  });

  tearDown(() async => db.close());

  test('read returns null for a missing key', () async {
    expect(await cache.read('banks'), isNull);
  });

  test('write then read round-trips payload and timestamp', () async {
    await cache.write('banks', '[{"id":1}]', 1234);
    final entry = await cache.read('banks');
    expect(entry, isNotNull);
    expect(entry!.payload, '[{"id":1}]');
    expect(entry.fetchedAt, 1234);
  });

  test('write replaces an existing entry for the same key', () async {
    await cache.write('banks', 'old', 1);
    await cache.write('banks', 'new', 2);
    final entry = await cache.read('banks');
    expect(entry!.payload, 'new');
    expect(entry.fetchedAt, 2);
  });

  test('clearAll removes every entry', () async {
    await cache.write('banks', 'a', 1);
    await cache.write('bills?bank_id=1', 'b', 2);
    await cache.clearAll();
    expect(await cache.read('banks'), isNull);
    expect(await cache.read('bills?bank_id=1'), isNull);
  });

  group('financeCacheKey', () {
    test('is just the path when there is no query', () {
      expect(financeCacheKey('/banks'), '/banks');
    });

    test('sorts query keys for stability', () {
      final a = financeCacheKey('/transactions', {'page': 1, 'size': 10});
      final b = financeCacheKey('/transactions', {'size': 10, 'page': 1});
      expect(a, b);
      expect(a, '/transactions?page=1&size=10');
    });

    test('joins list values with commas', () {
      final key = financeCacheKey('/transactions', {
        'types': ['income', 'expense'],
      });
      expect(key, '/transactions?types=income,expense');
    });
  });
}
