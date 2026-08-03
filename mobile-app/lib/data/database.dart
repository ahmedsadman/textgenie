import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

/// Opens (and migrates) the shared sqflite database.
///
/// Both the UI isolate and background isolates open their own connection to the
/// same file, so this must be safe to call from anywhere.
class AppDatabase {
  const AppDatabase._();

  static const String fileName = 'textgenie.db';
  static const String table = 'sms_records';
  static const int _version = 1;

  static Future<Database> open() async {
    final path = p.join(await getDatabasesPath(), fileName);
    return openDatabase(path, version: _version, onCreate: createSchema);
  }

  /// Creates the schema. Public so tests can build an in-memory database.
  static Future<void> createSchema(Database db, int version) async {
    await db.execute('''
      CREATE TABLE $table (
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
    // Dedupe overlapping foreground / background / cold-start reads of one SMS.
    await db.execute('''
      CREATE UNIQUE INDEX idx_sms_unique
      ON $table (sender, timestamp, content)
    ''');
  }
}
