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

  test('history caps successes to the limit, newest first', () async {
    for (var i = 0; i < 25; i++) {
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
    expect(history.length, kHistoryLimit);
    expect(history.first.content, 'm24');
  });

  test('history keeps all failures plus newest limit successes', () async {
    for (var i = 0; i < 25; i++) {
      await repo.insertIfNew(
        rec(
          content: 's$i',
          timestamp: i,
          status: SmsStatus.success,
          updatedAt: i,
        ),
      );
    }
    for (var i = 0; i < 5; i++) {
      await repo.insertIfNew(
        rec(
          content: 'f$i',
          timestamp: 1000 + i,
          status: SmsStatus.failure,
          updatedAt: 1000 + i,
        ),
      );
    }

    final history = await repo.history();
    final failures = history.where((r) => r.status == SmsStatus.failure);
    final successes = history.where((r) => r.status == SmsStatus.success);
    expect(failures.length, 5); // all failures survive the success cap
    expect(successes.length, kHistoryLimit);
    // Newest-updated first: failures (updatedAt 1000+) precede successes.
    expect(history.first.content, 'f4');
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

  test('countRetrying counts queued/sending with attempts >= 1', () async {
    await repo.insertIfNew(
      rec(content: 'retry-q', status: SmsStatus.queued, attempts: 2),
    );
    await repo.insertIfNew(
      rec(content: 'retry-s', status: SmsStatus.sending, attempts: 1),
    );
    // Offline-only / brand new: still in flight but no real attempt yet.
    await repo.insertIfNew(
      rec(content: 'offline', status: SmsStatus.queued, attempts: 0),
    );
    // Terminal rows never count regardless of attempts.
    await repo.insertIfNew(
      rec(content: 'failed', status: SmsStatus.failure, attempts: 10),
    );

    expect(await repo.countRetrying(), 2);
  });

  test('prune caps successes and keeps in-flight rows', () async {
    for (var i = 0; i < 25; i++) {
      await repo.insertIfNew(
        rec(
          content: 's$i',
          timestamp: i,
          status: SmsStatus.success,
          updatedAt: i,
        ),
      );
    }
    await repo.insertIfNew(
      rec(content: 'q', timestamp: 100, status: SmsStatus.queued, attempts: 1),
    );
    await repo.insertIfNew(
      rec(content: 'sn', timestamp: 101, status: SmsStatus.sending),
    );

    await repo.prune(failureCutoff: 0);

    final successes = (await repo.history()).where(
      (r) => r.status == SmsStatus.success,
    );
    expect(successes.length, kHistoryLimit); // capped to newest 20
    expect(successes.map((r) => r.content), contains('s24'));
    expect(successes.map((r) => r.content), isNot(contains('s0')));
    // In-flight rows survive.
    expect(
      (await repo.queued()).map((r) => r.content),
      containsAll(['q', 'sn']),
    );
  });

  test('prune deletes failures older than the cutoff, keeps recent', () async {
    await repo.insertIfNew(
      rec(content: 'old', status: SmsStatus.failure, updatedAt: 100),
    );
    await repo.insertIfNew(
      rec(content: 'recent', status: SmsStatus.failure, updatedAt: 900),
    );

    await repo.prune(failureCutoff: 500);

    final failures = (await repo.history()).where(
      (r) => r.status == SmsStatus.failure,
    );
    expect(failures.map((r) => r.content), ['recent']);
  });
}
