import 'package:another_telephony/telephony.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:sqflite/sqflite.dart';
import 'package:textgenie/data/settings_repository.dart';
import 'package:textgenie/data/sms_repository.dart';
import 'package:textgenie/models/sms_record.dart';
import 'package:textgenie/services/app_services.dart';
import 'package:textgenie/services/connectivity_service.dart';
import 'package:textgenie/services/contact_resolver.dart';
import 'package:textgenie/services/flush_service.dart';
import 'package:textgenie/services/notification_service.dart';
import 'package:textgenie/services/webhook_client.dart';

class MockDatabase extends Mock implements Database {}

class MockRepo extends Mock implements SmsRepository {}

class MockSettings extends Mock implements SettingsRepository {}

class MockContactResolver extends Mock implements ContactResolver {}

class MockConnectivity extends Mock implements ConnectivityService {}

class MockWebhookClient extends Mock implements WebhookClient {}

class MockNotifications extends Mock implements NotificationService {}

class MockFlushService extends Mock implements FlushService {}

class MockSmsMessage extends Mock implements SmsMessage {}

void main() {
  late MockRepo repo;
  late MockSettings settings;
  late MockFlushService flush;
  late AppServices services;

  setUpAll(() {
    registerFallbackValue(
      const SmsRecord(sender: '+100', content: 'x', timestamp: 0),
    );
  });

  setUp(() {
    repo = MockRepo();
    settings = MockSettings();
    flush = MockFlushService();
    services = AppServices(
      database: MockDatabase(),
      smsRepository: repo,
      settings: settings,
      contactResolver: MockContactResolver(),
      connectivity: MockConnectivity(),
      webhookClient: MockWebhookClient(),
      notifications: MockNotifications(),
      flushService: flush,
    );

    when(() => settings.resolveContacts).thenReturn(false);
    when(() => repo.insertIfNew(any())).thenAnswer((_) async => 1);
    when(() => flush.flush()).thenAnswer((_) async {});
    when(
      () => repo.prune(failureCutoff: any(named: 'failureCutoff')),
    ).thenAnswer((_) async {});
  });

  SmsMessage message() {
    final m = MockSmsMessage();
    when(() => m.address).thenReturn('+8801712345678');
    when(() => m.body).thenReturn('hello');
    when(() => m.date).thenReturn(1719000000000);
    return m;
  }

  test('handleIncomingSms prunes after flush with a 30-day cutoff', () async {
    final before = DateTime.now().millisecondsSinceEpoch;
    await services.handleIncomingSms(message());
    final after = DateTime.now().millisecondsSinceEpoch;

    // Prune must run after delivery so it never delays SMS processing.
    final order = verifyInOrder([
      () => flush.flush(),
      () => repo.prune(failureCutoff: captureAny(named: 'failureCutoff')),
    ]);

    final cutoff = order[1].captured.single as int;
    final retention = kFailureRetention.inMilliseconds;
    expect(cutoff, inInclusiveRange(before - retention, after - retention));
  });

  test('handleIncomingSms skips empty messages entirely', () async {
    final m = MockSmsMessage();
    when(() => m.address).thenReturn('');
    when(() => m.body).thenReturn('');
    when(() => m.date).thenReturn(0);

    await services.handleIncomingSms(m);

    verifyNever(() => repo.insertIfNew(any()));
    verifyNever(() => flush.flush());
    verifyNever(() => repo.prune(failureCutoff: any(named: 'failureCutoff')));
  });
}
