import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:textgenie/data/database.dart';
import 'package:textgenie/data/finance_cache.dart';
import 'package:textgenie/data/finance_repository.dart';
import 'package:textgenie/data/settings_repository.dart';
import 'package:textgenie/services/api_client.dart';
import 'package:textgenie/utils/api_config.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockSettings extends Mock implements SettingsRepository {}

class FakeApiConfig extends Fake implements ApiConfig {}

void main() {
  late Database db;
  late FinanceCache cache;
  late MockApiClient api;
  late MockSettings settings;
  late FinanceRepository repo;

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    registerFallbackValue(FakeApiConfig());
  });

  setUp(() async {
    db = await databaseFactory.openDatabase(
      inMemoryDatabasePath,
      options: OpenDatabaseOptions(
        version: 3,
        onCreate: AppDatabase.createSchema,
      ),
    );
    cache = FinanceCache(db);
    api = MockApiClient();
    settings = MockSettings();
    when(() => settings.webhookUrl).thenReturn('https://host/api/webhook/tok');
    repo = FinanceRepository(
      api: api,
      cache: cache,
      settings: settings,
      nowMs: () => 5000,
    );
  });

  tearDown(() async => db.close());

  void stubBanks(Object? response) {
    when(
      () => api.get(any(), '/banks', query: any(named: 'query')),
    ).thenAnswer((_) async => response);
  }

  test('successful fetch returns fresh data and writes cache', () async {
    stubBanks([
      {
        'id': 1,
        'name': 'Checking',
        'account_type': 'deposit',
        'card_digits': null,
        'last_balance': '100.00',
        'last_balance_at': null,
        'created_at': '2025-01-01T00:00:00Z',
      },
    ]);

    final result = await repo.banks();
    expect(result.stale, isFalse);
    expect(result.data.single.name, 'Checking');
    expect(result.fetchedAt, DateTime.fromMillisecondsSinceEpoch(5000));

    // Cache was populated under the '/banks' key.
    expect(await cache.read('/banks'), isNotNull);
  });

  test('falls back to cached data (stale) when the fetch fails', () async {
    stubBanks([
      {
        'id': 1,
        'name': 'Cached Bank',
        'account_type': 'deposit',
        'card_digits': null,
        'last_balance': '1.00',
        'last_balance_at': null,
        'created_at': '2025-01-01T00:00:00Z',
      },
    ]);
    await repo.banks(); // populate cache

    when(
      () => api.get(any(), '/banks', query: any(named: 'query')),
    ).thenThrow(ApiException.network());

    final result = await repo.banks();
    expect(result.stale, isTrue);
    expect(result.data.single.name, 'Cached Bank');
  });

  test('rethrows when the fetch fails and nothing is cached', () async {
    when(
      () => api.get(any(), '/banks', query: any(named: 'query')),
    ).thenThrow(ApiException.network());

    await expectLater(repo.banks(), throwsA(isA<ApiException>()));
  });

  test('throws unauthorized when no webhook URL is configured', () async {
    when(() => settings.webhookUrl).thenReturn(null);

    await expectLater(
      repo.banks(),
      throwsA(
        isA<ApiException>().having(
          (e) => e.kind,
          'kind',
          ApiErrorKind.unauthorized,
        ),
      ),
    );
    verifyNever(() => api.get(any(), any(), query: any(named: 'query')));
  });
}
