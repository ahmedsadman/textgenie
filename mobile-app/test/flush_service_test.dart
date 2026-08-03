import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:textgenie/data/settings_repository.dart';
import 'package:textgenie/data/sms_repository.dart';
import 'package:textgenie/models/sms_record.dart';
import 'package:textgenie/services/connectivity_service.dart';
import 'package:textgenie/services/flush_service.dart';
import 'package:textgenie/services/webhook_client.dart';

class MockRepo extends Mock implements SmsRepository {}

class MockClient extends Mock implements WebhookClient {}

class MockConnectivity extends Mock implements ConnectivityService {}

class MockSettings extends Mock implements SettingsRepository {}

SmsRecord _record({int id = 1, int attempts = 0}) => SmsRecord(
  id: id,
  sender: '+8801712345678',
  content: 'hello',
  timestamp: 1719000000000,
  attempts: attempts,
);

void main() {
  late MockRepo repo;
  late MockClient client;
  late MockConnectivity connectivity;
  late MockSettings settings;
  late List<Duration> slept;

  FlushService build() => FlushService(
    repository: repo,
    client: client,
    connectivity: connectivity,
    settings: settings,
    clock: () => 0,
    sleep: (d) async => slept.add(d),
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
    slept = [];

    when(() => settings.webhookUrl).thenReturn('https://example.com/hook');
    when(() => connectivity.isOnline()).thenAnswer((_) async => true);
    when(() => repo.reclaimStale(any())).thenAnswer((_) async {});
    when(() => repo.claim(any(), any())).thenAnswer((_) async => true);
    when(
      () => repo.updateStatus(
        any(),
        any(),
        attempts: any(named: 'attempts'),
        lastError: any(named: 'lastError'),
        updatedAt: any(named: 'updatedAt'),
      ),
    ).thenAnswer((_) async {});
  });

  List<SmsStatus> capturedStatuses() => verify(
    () => repo.updateStatus(
      any(),
      captureAny(),
      attempts: any(named: 'attempts'),
      lastError: any(named: 'lastError'),
      updatedAt: any(named: 'updatedAt'),
    ),
  ).captured.cast<SmsStatus>();

  test('does nothing when no webhook URL configured', () async {
    when(() => settings.webhookUrl).thenReturn(null);
    await build().flush();
    verifyNever(() => repo.queued());
    verifyNever(() => client.send(any(), any()));
  });

  test('does nothing when offline', () async {
    when(() => connectivity.isOnline()).thenAnswer((_) async => false);
    await build().flush();
    verifyNever(() => repo.claim(any(), any()));
    verifyNever(() => client.send(any(), any()));
  });

  test('reclaims stale sending rows before draining', () async {
    when(() => repo.queued()).thenAnswer((_) async => []);
    await build().flush();
    verify(() => repo.reclaimStale(any())).called(1);
  });

  test('skips a record already claimed by another isolate', () async {
    when(() => repo.queued()).thenAnswer((_) async => [_record()]);
    when(() => repo.claim(any(), any())).thenAnswer((_) async => false);

    await build().flush();

    verifyNever(() => client.send(any(), any()));
  });

  test('marks success on 2xx', () async {
    when(() => repo.queued()).thenAnswer((_) async => [_record()]);
    when(
      () => client.send(any(), any()),
    ).thenAnswer((_) async => const WebhookResult.success());

    await build().flush();

    verify(() => repo.claim(1, any())).called(1);
    expect(capturedStatuses(), [SmsStatus.success]);
    verify(() => client.send('https://example.com/hook', any())).called(1);
  });

  test('retries with exponential backoff then succeeds', () async {
    var calls = 0;
    when(() => repo.queued()).thenAnswer((_) async => [_record()]);
    when(() => client.send(any(), any())).thenAnswer((_) async {
      calls++;
      return calls < 3
          ? const WebhookResult.failure('HTTP 500')
          : const WebhookResult.success();
    });

    await build().flush();

    expect(calls, 3);
    // Two failures -> two backoffs: 2^1, 2^2 seconds.
    expect(slept, [const Duration(seconds: 2), const Duration(seconds: 4)]);
    // Ownership kept (sending) between retries, then success.
    expect(capturedStatuses(), [
      SmsStatus.sending,
      SmsStatus.sending,
      SmsStatus.success,
    ]);
  });

  test('marks failure after 5 attempts', () async {
    when(() => repo.queued()).thenAnswer((_) async => [_record()]);
    when(
      () => client.send(any(), any()),
    ).thenAnswer((_) async => const WebhookResult.failure('HTTP 500'));

    await build().flush();

    verify(() => client.send(any(), any())).called(FlushService.maxAttempts);
    expect(capturedStatuses().last, SmsStatus.failure);
    // 4 backoffs between 5 attempts.
    expect(slept.length, FlushService.maxAttempts - 1);
  });

  test('resumes attempt count from a partially-failed record', () async {
    // Record already failed 4 times; one more failure should mark it failed.
    when(() => repo.queued()).thenAnswer((_) async => [_record(attempts: 4)]);
    when(
      () => client.send(any(), any()),
    ).thenAnswer((_) async => const WebhookResult.failure('HTTP 500'));

    await build().flush();

    verify(() => client.send(any(), any())).called(1);
    expect(capturedStatuses().last, SmsStatus.failure);
    expect(slept, isEmpty);
  });

  test('stops and requeues when device goes offline mid-flush', () async {
    var online = true;
    when(() => connectivity.isOnline()).thenAnswer((_) async => online);
    when(() => repo.queued()).thenAnswer((_) async => [_record()]);
    when(() => client.send(any(), any())).thenAnswer((_) async {
      online = false; // drop connection after first failed send
      return const WebhookResult.failure('HTTP 500');
    });

    await build().flush();

    // Ends queued (released) because it abandoned on going offline.
    expect(capturedStatuses().last, SmsStatus.queued);
    verify(() => client.send(any(), any())).called(1);
  });
}
