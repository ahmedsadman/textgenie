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
import 'notification_service.dart';
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
    required this.notifications,
    required this.flushService,
  });

  final Database database;
  final SmsRepository smsRepository;
  final SettingsRepository settings;
  final ContactResolver contactResolver;
  final ConnectivityService connectivity;
  final WebhookClient webhookClient;
  final NotificationService notifications;
  final FlushService flushService;

  factory AppServices.from({
    required Database database,
    required SharedPreferences prefs,
  }) {
    final smsRepository = SmsRepository(database);
    final settings = SettingsRepository(prefs);
    final connectivity = ConnectivityService();
    final webhookClient = WebhookClient();
    final notifications = NotificationService();
    return AppServices(
      database: database,
      smsRepository: smsRepository,
      settings: settings,
      contactResolver: ContactResolver(),
      connectivity: connectivity,
      webhookClient: webhookClient,
      notifications: notifications,
      flushService: FlushService(
        repository: smsRepository,
        client: webhookClient,
        connectivity: connectivity,
        settings: settings,
        notifications: notifications,
      ),
    );
  }

  /// Builds a fully standalone bundle (opens its own DB + prefs). Use from
  /// background isolates, which must init notifications themselves to be able
  /// to post failures.
  static Future<AppServices> bootstrap() async {
    final database = await AppDatabase.open();
    final prefs = await SharedPreferences.getInstance();
    final services = AppServices.from(database: database, prefs: prefs);
    await services.notifications.init();
    return services;
  }

  /// Manual retry entry point: returns every failed message to the queue for a
  /// single re-send attempt, then flushes.
  Future<void> requeueFailed() async {
    await smsRepository.requeueFailed(
      DateTime.now().millisecondsSinceEpoch,
      attempts: FlushService.maxAttempts - 1,
    );
    await flushService.flush();
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
