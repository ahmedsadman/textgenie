import 'package:sqflite/sqflite.dart';

import '../models/sms_record.dart';
import 'database.dart';

/// Default cap for [SmsRepository.history]. Exposed so the UI can display it.
const int kHistoryLimit = 10;

/// CRUD + queue/history queries for captured SMS.
class SmsRepository {
  SmsRepository(this._db);

  final Database _db;
  static const _table = AppDatabase.table;

  /// Inserts a new record, ignoring duplicates (same sender+timestamp+content).
  ///
  /// Returns the row id, or null when the SMS was already stored.
  Future<int?> insertIfNew(SmsRecord record) async {
    final map = record.toDbMap()..remove('id');
    final id = await _db.insert(
      _table,
      map,
      conflictAlgorithm: ConflictAlgorithm.ignore,
    );
    return id == 0 ? null : id;
  }

  /// Queued + in-flight records, oldest first. Used by the UI Queued section,
  /// so it includes rows still waiting on a scheduled `next_attempt_at`.
  Future<List<SmsRecord>> queued() => _query(
    where: 'status IN (?, ?)',
    whereArgs: [SmsStatus.queued.name, SmsStatus.sending.name],
    orderBy: 'timestamp ASC',
  );

  /// Queued records eligible for delivery right now, oldest first. Rows whose
  /// `next_attempt_at` is still in the future are skipped. `sending` rows are
  /// excluded — [reclaimStale] returns orphaned ones to `queued` first.
  Future<List<SmsRecord>> dueForDelivery(int now) => _query(
    where: 'status = ? AND (next_attempt_at IS NULL OR next_attempt_at <= ?)',
    whereArgs: [SmsStatus.queued.name, now],
    orderBy: 'timestamp ASC',
  );

  /// Number of records that have exhausted their retries.
  Future<int> countFailed() async {
    final rows = await _db.rawQuery(
      'SELECT COUNT(*) AS c FROM $_table WHERE status = ?',
      [SmsStatus.failure.name],
    );
    return Sqflite.firstIntValue(rows) ?? 0;
  }

  /// Manual retry: returns all failed rows to `queued` for one more attempt.
  ///
  /// [attempts] is pre-set to `maxAttempts - 1` so the single-send flush tries
  /// exactly once and, on failure, transitions straight back to `failure`.
  Future<void> requeueFailed(int now, {required int attempts}) async {
    await _db.update(
      _table,
      {
        'status': SmsStatus.queued.name,
        'attempts': attempts,
        'next_attempt_at': null,
        'updated_at': now,
      },
      where: 'status = ?',
      whereArgs: [SmsStatus.failure.name],
    );
  }

  /// Last [limit] finished records, most recently updated first.
  Future<List<SmsRecord>> history({int limit = kHistoryLimit}) => _query(
    where: 'status IN (?, ?)',
    whereArgs: [SmsStatus.success.name, SmsStatus.failure.name],
    orderBy: 'updated_at DESC',
    limit: limit,
  );

  Future<void> updateStatus(
    int id,
    SmsStatus status, {
    int? attempts,
    String? lastError,
    required int updatedAt,
    int? nextAttemptAt,
  }) async {
    await _db.update(
      _table,
      {
        'status': status.name,
        'attempts': ?attempts,
        // Null-aware: omit so an in-flight retry keeps its prior error.
        'last_error': ?lastError,
        'updated_at': updatedAt,
        // NOT null-aware: always written so the scheduled retry can be cleared
        // (success / terminal failure pass null) or set (requeue passes a
        // future time). A null-aware entry would omit the key and leave a
        // stale schedule behind.
        'next_attempt_at': nextAttemptAt,
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  /// Atomically claims a queued row for delivery (queued -> sending).
  ///
  /// Returns true only if this caller won the claim. Prevents two isolates
  /// (e.g. the WorkManager task and the foreground app) from sending the same
  /// message twice.
  Future<bool> claim(int id, int updatedAt) async {
    final count = await _db.update(
      _table,
      {'status': SmsStatus.sending.name, 'updated_at': updatedAt},
      where: 'id = ? AND status = ?',
      whereArgs: [id, SmsStatus.queued.name],
    );
    return count == 1;
  }

  /// Requeues rows stuck in `sending` (orphaned by a killed isolate) whose last
  /// update predates [olderThan] (epoch ms), so they can be retried.
  Future<void> reclaimStale(int olderThan) async {
    await _db.update(
      _table,
      {'status': SmsStatus.queued.name},
      where: 'status = ? AND updated_at < ?',
      whereArgs: [SmsStatus.sending.name, olderThan],
    );
  }

  Future<List<SmsRecord>> _query({
    required String where,
    required List<Object?> whereArgs,
    required String orderBy,
    int? limit,
  }) async {
    final rows = await _db.query(
      _table,
      where: where,
      whereArgs: whereArgs,
      orderBy: orderBy,
      limit: limit,
    );
    return rows.map(SmsRecord.fromDbMap).toList();
  }
}
