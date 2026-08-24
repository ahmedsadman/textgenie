import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:textgenie/data/settings_repository.dart';
import 'package:textgenie/data/sms_repository.dart';
import 'package:textgenie/models/sms_record.dart';
import 'package:textgenie/services/connectivity_service.dart';
import 'package:textgenie/services/flush_service.dart';
import 'package:textgenie/services/notification_service.dart';
import 'package:textgenie/services/webhook_client.dart';

class MockRepo extends Mock implements SmsRepository {}

class MockClient extends Mock implements WebhookClient {}

class MockConnectivity extends Mock implements ConnectivityService {}

class MockSettings extends Mock implements SettingsRepository {}

class MockNotifications extends Mock implements NotificationService {}

SmsRecord _record({int id = 1, int attempts = 0, int? nextAttemptAt}) =>
    SmsRecord(
      id: id,
      sender: '+8801712345678',
      content: 'hello',
      timestamp: 1719000000000,
      attempts: attempts,
      nextAttemptAt: nextAttemptAt,
    );

void main() {
  late MockRepo repo;
  late MockClient client;
  late MockConnectivity connectivity;
  late MockSettings settings;
  late MockNotifications notifications;

  FlushService build({int clock = 0}) => FlushService(
    repository: repo,
    client: client,
    connectivity: connectivity,
    settings: settings,
    notifications: notifications,
    clock: () => clock,
  );

  setUpAll(() {
    registerFallbackValue(SmsStatus.queued);
    registerFallbackValue(_record());
  });

  setUp(() {
    repo = MockRepo();
    client = MockClient();
    connectivity = MockConnectivity();
    settings = MockSettings();
    notifications = MockNotifications();

    when(() => settings.webhookUrl).thenReturn('https://example.com/hook');
    when(() => connectivity.isOnline()).thenAnswer((_) async => true);
    when(() => repo.reclaimStale(any())).thenAnswer((_) async {});
    when(() => repo.claim(any(), any())).thenAnswer((_) async => true);
    when(() => repo.countFailed()).thenAnswer((_) async => 0);
    when(() => repo.dueForDelivery(any())).thenAnswer((_) async => []);
    when(() => notifications.reconcileFailures(any())).thenAnswer((_) async {});
    when(
      () => repo.updateStatus(
        any(),
        any(),
        attempts: any(named: 'attempts'),
        lastError: any(named: 'lastError'),
        updatedAt: any(named: 'updatedAt'),
        nextAttemptAt: any(named: 'nextAttemptAt'),
      ),
    ).thenAnswer((_) async {});
  });

  /// Captures [status, nextAttemptAt] of the single update a delivery makes.
  List<Object?> capturedUpdate() => verify(
    () => repo.updateStatus(
      any(),
      captureAny(),
      attempts: any(named: 'attempts'),
      lastError: any(named: 'lastError'),
      updatedAt: any(named: 'updatedAt'),
      nextAttemptAt: captureAny(named: 'nextAttemptAt'),
    ),
  ).captured;

  test('does nothing when no webhook URL configured', () async {
    when(() => settings.webhookUrl).thenReturn(null);
    await build().flush();
    verifyNever(() => repo.dueForDelivery(any()));
    verifyNever(() => client.send(any(), any()));
    verifyNever(() => notifications.reconcileFailures(any()));
  });

  test('does nothing when offline', () async {
    when(() => connectivity.isOnline()).thenAnswer((_) async => false);
    await build().flush();
    verifyNever(() => repo.claim(any(), any()));
    verifyNever(() => client.send(any(), any()));
  });

  test('reclaims stale sending rows before draining', () async {
    await build().flush();
    verify(() => repo.reclaimStale(any())).called(1);
  });

  test('drains only due records', () async {
    await build().flush();
    verify(() => repo.dueForDelivery(any())).called(1);
    verifyNever(() => repo.queued());
  });

  test('skips a record already claimed by another isolate', () async {
    when(() => repo.dueForDelivery(any())).thenAnswer((_) async => [_record()]);
    when(() => repo.claim(any(), any())).thenAnswer((_) async => false);

    await build().flush();

    verifyNever(() => client.send(any(), any()));
  });

  test('marks success and clears the schedule on 2xx', () async {
    when(() => repo.dueForDelivery(any())).thenAnswer((_) async => [_record()]);
    when(
      () => client.send(any(), any()),
    ).thenAnswer((_) async => const WebhookResult.success());

    await build().flush();

    verify(() => repo.claim(1, any())).called(1);
    verify(() => client.send('https://example.com/hook', any())).called(1);
    expect(capturedUpdate(), [SmsStatus.success, null]);
  });

  test('sends only once per pass, rescheduling on failure', () async {
    when(() => repo.dueForDelivery(any())).thenAnswer((_) async => [_record()]);
    when(
      () => client.send(any(), any()),
    ).thenAnswer((_) async => const WebhookResult.failure('HTTP 500'));

    await build().flush();

    // No in-loop retry: exactly one send, row requeued for a later flush.
    verify(() => client.send(any(), any())).called(1);
    expect(capturedUpdate(), [SmsStatus.queued, 15000]);
  });

  test('reschedules with capped-exponential backoff', () async {
    // attempts-so-far -> next_attempt_at with clock pinned at 0.
    const expected = {
      0: 15000, // 15s
      1: 60000, // 1m
      2: 240000, // 4m
      3: 960000, // 16m
      4: 3840000, // ~1.1h
      5: 15360000, // ~4.3h
      6: 21600000, // capped at 6h
      8: 21600000, // still capped
    };

    for (final entry in expected.entries) {
      when(
        () => repo.dueForDelivery(any()),
      ).thenAnswer((_) async => [_record(attempts: entry.key)]);
      when(
        () => client.send(any(), any()),
      ).thenAnswer((_) async => const WebhookResult.failure('HTTP 500'));

      await build().flush();

      expect(capturedUpdate(), [
        SmsStatus.queued,
        entry.value,
      ], reason: 'attempts=${entry.key}');
      reset(repo);
      // Re-stub the reset mock for the next iteration.
      when(() => repo.reclaimStale(any())).thenAnswer((_) async {});
      when(() => repo.claim(any(), any())).thenAnswer((_) async => true);
      when(() => repo.countFailed()).thenAnswer((_) async => 0);
      when(
        () => repo.updateStatus(
          any(),
          any(),
          attempts: any(named: 'attempts'),
          lastError: any(named: 'lastError'),
          updatedAt: any(named: 'updatedAt'),
          nextAttemptAt: any(named: 'nextAttemptAt'),
        ),
      ).thenAnswer((_) async {});
    }
  });

  test('marks failure with no schedule after the final attempt', () async {
    // attempts already at maxAttempts-1: one more failure is terminal.
    when(() => repo.dueForDelivery(any())).thenAnswer(
      (_) async => [_record(attempts: FlushService.maxAttempts - 1)],
    );
    when(
      () => client.send(any(), any()),
    ).thenAnswer((_) async => const WebhookResult.failure('HTTP 500'));
    when(() => repo.countFailed()).thenAnswer((_) async => 1);

    await build().flush();

    verify(() => client.send(any(), any())).called(1);
    expect(capturedUpdate(), [SmsStatus.failure, null]);
    verify(() => notifications.reconcileFailures(1)).called(1);
  });

  test('reconciles the failure notification each flush', () async {
    when(() => repo.countFailed()).thenAnswer((_) async => 3);
    await build().flush();
    verify(() => notifications.reconcileFailures(3)).called(1);
  });

  test('releases the row unchanged when it goes offline mid-send', () async {
    var online = true;
    when(() => connectivity.isOnline()).thenAnswer((_) async => online);
    when(
      () => repo.dueForDelivery(any()),
    ).thenAnswer((_) async => [_record(nextAttemptAt: 99)]);
    when(() => client.send(any(), any())).thenAnswer((_) async {
      online = false; // connection dropped during the request
      return const WebhookResult.failure('HTTP 500');
    });

    await build().flush();

    verify(() => client.send(any(), any())).called(1);
    // Requeued, still due at its original schedule (not counted as an attempt).
    expect(capturedUpdate(), [SmsStatus.queued, 99]);
  });
}
