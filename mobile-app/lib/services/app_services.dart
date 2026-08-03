import 'package:another_telephony/telephony.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';

import '../data/database.dart';
import '../data/settings_repository.dart';
import '../data/sms_repository.dart';
import '../models/sms_record.dart';
import 'connectivity_service.dart';
import 'contact_resolver.dart';
import 'flush_service.dart';
import 'webhook_client.dart';

/// Wires the core services together. Constructed once for the UI isolate and
/// freshly (from scratch) inside background isolates, since those cannot share
/// the UI isolate's objects.
class AppServices {
  AppServices({
    required this.database,
    required this.smsRepository,
    required this.settings,
    required this.contactResolver,
    required this.connectivity,
    required this.webhookClient,
    required this.flushService,
  });

  final Database database;
  final SmsRepository smsRepository;
  final SettingsRepository settings;
  final ContactResolver contactResolver;
  final ConnectivityService connectivity;
  final WebhookClient webhookClient;
  final FlushService flushService;

  factory AppServices.from({
    required Database database,
    required SharedPreferences prefs,
  }) {
    final smsRepository = SmsRepository(database);
    final settings = SettingsRepository(prefs);
    final connectivity = ConnectivityService();
    final webhookClient = WebhookClient();
    return AppServices(
      database: database,
      smsRepository: smsRepository,
      settings: settings,
      contactResolver: ContactResolver(),
      connectivity: connectivity,
      webhookClient: webhookClient,
      flushService: FlushService(
        repository: smsRepository,
        client: webhookClient,
        connectivity: connectivity,
        settings: settings,
      ),
    );
  }

  /// Builds a fully standalone bundle (opens its own DB + prefs). Use from
  /// background isolates.
  static Future<AppServices> bootstrap() async {
    final database = await AppDatabase.open();
    final prefs = await SharedPreferences.getInstance();
    return AppServices.from(database: database, prefs: prefs);
  }

  /// Persists an incoming SMS (deduped) and attempts to flush the queue.
  Future<void> handleIncomingSms(SmsMessage message) async {
    final sender = (message.address ?? '').trim();
    final content = message.body ?? '';
    if (sender.isEmpty || content.isEmpty) return;

    final contactName = settings.resolveContacts
        ? await contactResolver.nameFor(sender)
        : null;

    final now = DateTime.now().millisecondsSinceEpoch;
    await smsRepository.insertIfNew(
      SmsRecord(
        sender: sender,
        contactName: contactName,
        content: content,
        timestamp: message.date ?? now,
        updatedAt: now,
      ),
    );

    await flushService.flush();
  }
}
