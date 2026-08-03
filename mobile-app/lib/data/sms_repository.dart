import 'package:sqflite/sqflite.dart';

import '../models/sms_record.dart';
import 'database.dart';

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

  /// Queued + in-flight records, oldest first (delivery order).
  Future<List<SmsRecord>> queued() => _query(
    where: 'status IN (?, ?)',
    whereArgs: [SmsStatus.queued.name, SmsStatus.sending.name],
    orderBy: 'timestamp ASC',
  );

  /// Last [limit] finished records, most recently updated first.
  Future<List<SmsRecord>> history({int limit = 10}) => _query(
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
  }) async {
    await _db.update(
      _table,
      {
        'status': status.name,
        'attempts': ?attempts,
        // Null-aware: omit so an in-flight retry keeps its prior error.
        'last_error': ?lastError,
        'updated_at': updatedAt,
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
