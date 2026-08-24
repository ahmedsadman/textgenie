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
    int attempts = 0,
    int updatedAt = 0,
    int? nextAttemptAt,
  }) => SmsRecord(
    sender: sender,
    content: content,
    timestamp: timestamp,
    status: status,
    attempts: attempts,
    updatedAt: updatedAt,
    nextAttemptAt: nextAttemptAt,
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

  test('updateStatus sets then clears next_attempt_at', () async {
    final id = await repo.insertIfNew(rec());
    await repo.updateStatus(
      id!,
      SmsStatus.queued,
      updatedAt: 10,
      nextAttemptAt: 5000,
    );
    expect((await repo.queued()).single.nextAttemptAt, 5000);

    // Success clears the schedule (passing null must actually null the column).
    await repo.updateStatus(
      id,
      SmsStatus.success,
      updatedAt: 20,
      nextAttemptAt: null,
    );
    expect((await repo.history()).single.nextAttemptAt, isNull);
  });

  test('dueForDelivery skips rows scheduled in the future', () async {
    await repo.insertIfNew(rec(content: 'due-null', timestamp: 3000));
    await repo.insertIfNew(
      rec(content: 'due-past', timestamp: 1000, nextAttemptAt: 400),
    );
    await repo.insertIfNew(
      rec(content: 'not-due', timestamp: 2000, nextAttemptAt: 999),
    );
    await repo.insertIfNew(
      rec(content: 'done', status: SmsStatus.success, timestamp: 500),
    );

    final due = await repo.dueForDelivery(500);

    // Oldest-first, future-scheduled and terminal rows excluded.
    expect(due.map((r) => r.content), ['due-past', 'due-null']);
  });

  test('countFailed counts only failed rows', () async {
    await repo.insertIfNew(rec(content: 'a', status: SmsStatus.failure));
    await repo.insertIfNew(rec(content: 'b', status: SmsStatus.failure));
    await repo.insertIfNew(rec(content: 'c', status: SmsStatus.success));
    await repo.insertIfNew(rec(content: 'd'));

    expect(await repo.countFailed(), 2);
  });

  test('requeueFailed requeues failures for one more attempt', () async {
    await repo.insertIfNew(
      rec(content: 'f', status: SmsStatus.failure, nextAttemptAt: 12345),
    );
    await repo.insertIfNew(rec(content: 'ok', status: SmsStatus.success));

    await repo.requeueFailed(777, attempts: 9);

    final requeued = (await repo.dueForDelivery(777)).single;
    expect(requeued.content, 'f');
    expect(requeued.status, SmsStatus.queued);
    expect(requeued.attempts, 9);
    expect(requeued.nextAttemptAt, isNull); // due immediately
    // The successful row is untouched.
    expect(await repo.countFailed(), 0);
    expect((await repo.history()).single.content, 'ok');
  });
}
