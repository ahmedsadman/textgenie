import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:textgenie/data/database.dart';

/// The v1 schema exactly as it shipped, before `next_attempt_at` existed.
Future<void> _createV1(Database db, int version) async {
  await db.execute('''
    CREATE TABLE ${AppDatabase.table} (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sender TEXT NOT NULL,
      contact_name TEXT,
      content TEXT NOT NULL,
      timestamp INTEGER NOT NULL,
      status TEXT NOT NULL,
      attempts INTEGER NOT NULL DEFAULT 0,
      last_error TEXT,
      updated_at INTEGER NOT NULL DEFAULT 0
    )
  ''');
}

void main() {
  late Directory dir;
  late String path;

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  setUp(() async {
    dir = await Directory.systemTemp.createTemp('textgenie_migration');
    path = p.join(dir.path, 'textgenie.db');
  });

  tearDown(() async {
    if (await dir.exists()) await dir.delete(recursive: true);
  });

  test('v1 -> v2 adds next_attempt_at and preserves existing rows', () async {
    var db = await databaseFactory.openDatabase(
      path,
      options: OpenDatabaseOptions(version: 1, onCreate: _createV1),
    );
    await db.insert(AppDatabase.table, {
      'sender': '+100',
      'content': 'legacy',
      'timestamp': 1000,
      'status': 'queued',
      'attempts': 2,
      'updated_at': 5,
    });
    await db.close();

    db = await databaseFactory.openDatabase(
      path,
      options: OpenDatabaseOptions(
        version: 2,
        onCreate: AppDatabase.createSchema,
        onUpgrade: AppDatabase.onUpgrade,
      ),
    );

    final columns = (await db.rawQuery(
      'PRAGMA table_info(${AppDatabase.table})',
    )).map((r) => r['name']).toList();
    expect(columns, contains('next_attempt_at'));

    final row = (await db.query(AppDatabase.table)).single;
    expect(row['content'], 'legacy');
    expect(row['attempts'], 2);
    expect(row['next_attempt_at'], isNull);

    await db.close();
  });

  test('v2 -> v3 adds finance_cache and preserves existing rows', () async {
    var db = await databaseFactory.openDatabase(
      path,
      options: OpenDatabaseOptions(
        version: 2,
        onCreate: _createV1,
        onUpgrade: AppDatabase.onUpgrade,
      ),
    );
    await db.insert(AppDatabase.table, {
      'sender': '+100',
      'content': 'legacy',
      'timestamp': 1000,
      'status': 'queued',
      'attempts': 0,
      'updated_at': 5,
    });
    await db.close();

    db = await databaseFactory.openDatabase(
      path,
      options: OpenDatabaseOptions(
        version: 3,
        onCreate: AppDatabase.createSchema,
        onUpgrade: AppDatabase.onUpgrade,
      ),
    );

    final tables = (await db.rawQuery(
      "SELECT name FROM sqlite_master WHERE type='table'",
    )).map((r) => r['name']).toList();
    expect(tables, contains(AppDatabase.financeCacheTable));

    // Existing SMS rows survive the upgrade.
    expect((await db.query(AppDatabase.table)).single['content'], 'legacy');

    // The new table is usable.
    await db.insert(AppDatabase.financeCacheTable, {
      'cache_key': '/banks',
      'payload': '[]',
      'fetched_at': 1,
    });
    expect((await db.query(AppDatabase.financeCacheTable)).length, 1);

    await db.close();
  });
}
