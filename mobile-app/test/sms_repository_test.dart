import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:textgenie/data/database.dart';
import 'package:textgenie/data/sms_repository.dart';
import 'package:textgenie/models/sms_record.dart';

void main() {
  late Database db;
  late SmsRepository repo;

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  setUp(() async {
    db = await databaseFactory.openDatabase(
      inMemoryDatabasePath,
      options: OpenDatabaseOptions(
        version: 1,
        onCreate: AppDatabase.createSchema,
      ),
    );
    repo = SmsRepository(db);
  });

  tearDown(() => db.close());

  SmsRecord rec({
    String sender = '+100',
    String content = 'hi',
    int timestamp = 1000,
    SmsStatus status = SmsStatus.queued,
    int updatedAt = 0,
  }) => SmsRecord(
    sender: sender,
    content: content,
    timestamp: timestamp,
    status: status,
    updatedAt: updatedAt,
  );

  test('insertIfNew returns id, then null for a duplicate', () async {
    final id = await repo.insertIfNew(rec());
    expect(id, isNotNull);
    final dupe = await repo.insertIfNew(rec());
    expect(dupe, isNull);
    expect((await repo.queued()).length, 1);
  });

  test(
    'same sender/timestamp but different content is not a duplicate',
    () async {
      await repo.insertIfNew(rec(content: 'a'));
      final second = await repo.insertIfNew(rec(content: 'b'));
      expect(second, isNotNull);
      expect((await repo.queued()).length, 2);
    },
  );

  test('queued returns queued + sending oldest first', () async {
    await repo.insertIfNew(rec(content: 'new', timestamp: 3000));
    await repo.insertIfNew(rec(content: 'old', timestamp: 1000));
    await repo.insertIfNew(rec(content: 'done', status: SmsStatus.success));

    final queued = await repo.queued();
    expect(queued.map((r) => r.content), ['old', 'new']);
  });

  test('history returns finished records, newest first, limited', () async {
    for (var i = 0; i < 12; i++) {
      await repo.insertIfNew(
        rec(
          content: 'm$i',
          timestamp: i,
          status: SmsStatus.success,
          updatedAt: i,
        ),
      );
    }
    final history = await repo.history();
    expect(history.length, 10);
    expect(history.first.content, 'm11');
  });

  test('claim succeeds once, second claim on same row fails', () async {
    final id = await repo.insertIfNew(rec());
    expect(await repo.claim(id!, 100), isTrue);
    expect(await repo.claim(id, 200), isFalse); // now sending, not queued
  });

  test('reclaimStale requeues only old sending rows', () async {
    final fresh = await repo.insertIfNew(rec(content: 'fresh'));
    final stale = await repo.insertIfNew(rec(content: 'stale'));
    await repo.claim(fresh!, 1000);
    await repo.claim(stale!, 100);

    await repo.reclaimStale(500); // only rows updated before 500

    // The stale row is claimable again; the fresh one is not.
    expect(await repo.claim(stale, 600), isTrue);
    expect(await repo.claim(fresh, 600), isFalse);
  });

  test('updateStatus persists status, attempts and error', () async {
    final id = await repo.insertIfNew(rec());
    await repo.updateStatus(
      id!,
      SmsStatus.failure,
      attempts: 5,
      lastError: 'HTTP 500',
      updatedAt: 42,
    );

    final failed = (await repo.history()).single;
    expect(failed.status, SmsStatus.failure);
    expect(failed.attempts, 5);
    expect(failed.lastError, 'HTTP 500');
  });
}
