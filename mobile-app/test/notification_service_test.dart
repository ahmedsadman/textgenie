import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:textgenie/services/notification_service.dart';

class MockPlugin extends Mock implements FlutterLocalNotificationsPlugin {}

void main() {
  late MockPlugin plugin;
  late NotificationService service;

  setUp(() {
    plugin = MockPlugin();
    service = NotificationService(plugin: plugin);
    when(
      () => plugin.show(any(), any(), any(), any()),
    ).thenAnswer((_) async {});
    when(() => plugin.cancel(any())).thenAnswer((_) async {});
  });

  test('posts a single generic notification when failures exist', () async {
    await service.reconcileFailures(3);

    // Always the same fixed id so repeats update rather than stack.
    verify(() => plugin.show(1, any(), any(), any())).called(1);
    verifyNever(() => plugin.cancel(any()));
  });

  test('cancels the notification when there are no failures', () async {
    await service.reconcileFailures(0);

    verify(() => plugin.cancel(1)).called(1);
    verifyNever(() => plugin.show(any(), any(), any(), any()));
  });
}
