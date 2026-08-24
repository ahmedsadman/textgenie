import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Posts a single, generic local notification summarising delivery failures.
///
/// The plugin's default constructor returns a process-wide singleton, so
/// [init] can run independently in the UI and WorkManager isolates and both
/// still target the same native notification.
class NotificationService {
  NotificationService({FlutterLocalNotificationsPlugin? plugin})
    : _plugin = plugin ?? FlutterLocalNotificationsPlugin();

  final FlutterLocalNotificationsPlugin _plugin;

  static const String _channelId = 'textgenie_failures';
  static const String _channelName = 'Delivery failures';
  static const String _channelDescription =
      'Alerts when messages cannot be delivered to your webhook';

  /// Fixed ids so repeated reconciles update (not stack) one notification each.
  static const int _failureNotificationId = 1;
  static const int _retryingNotificationId = 2;

  Future<void> init() async {
    const settings = InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
    );
    await _plugin.initialize(settings);
    // Pre-create the channel so background-isolate posts have somewhere to land.
    await _plugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.createNotificationChannel(
          const AndroidNotificationChannel(
            _channelId,
            _channelName,
            description: _channelDescription,
            importance: Importance.defaultImportance,
          ),
        );
  }

  /// Shows the terminal-failure notification when [count] > 0, cancels it at 0.
  /// Called at the end of every flush so it auto-clears once failures succeed or
  /// are retried away.
  Future<void> reconcileFailures(int count) => _reconcile(
    id: _failureNotificationId,
    title: 'Delivery failed',
    count: count,
    body: (noun) => "$count $noun couldn't be delivered to your webhook",
  );

  /// Shows an early alert when [count] > 0 messages have first failed a real
  /// request and are being retried, cancels it at 0. Distinct id/title from
  /// [reconcileFailures] so the two coexist.
  Future<void> reconcileRetrying(int count) => _reconcile(
    id: _retryingNotificationId,
    title: 'Delivery failing',
    count: count,
    body: (noun) =>
        "$count $noun couldn't be delivered yet and are being retried",
  );

  Future<void> _reconcile({
    required int id,
    required String title,
    required int count,
    required String Function(String noun) body,
  }) async {
    if (count <= 0) {
      await _plugin.cancel(id);
      return;
    }
    final noun = count == 1 ? 'message' : 'messages';
    await _plugin.show(
      id,
      title,
      body(noun),
      const NotificationDetails(
        android: AndroidNotificationDetails(
          _channelId,
          _channelName,
          channelDescription: _channelDescription,
          importance: Importance.defaultImportance,
          priority: Priority.defaultPriority,
        ),
      ),
    );
  }
}
