import 'dart:async';
import 'dart:math';

import '../data/settings_repository.dart';
import '../data/sms_repository.dart';
import '../models/sms_record.dart';
import 'connectivity_service.dart';
import 'notification_service.dart';
import 'webhook_client.dart';

/// Drains the queue to the webhook, sending each due message exactly once per
/// pass. Failures are rescheduled with a capped-exponential backoff persisted in
/// `next_attempt_at`; the existing triggers (foreground resume, incoming-SMS
/// isolate, WorkManager tick) drive later retries. No in-loop sleeping — so a
/// `sending` row only ever covers a live HTTP POST.
class FlushService {
  FlushService({
    required this.repository,
    required this.client,
    required this.connectivity,
    required this.settings,
    required this.notifications,
    int Function()? clock,
  }) : _clock = clock ?? (() => DateTime.now().millisecondsSinceEpoch);

  final SmsRepository repository;
  final WebhookClient client;
  final ConnectivityService connectivity;
  final SettingsRepository settings;
  final NotificationService notifications;
  final int Function() _clock;

  /// Max delivery attempts before a record is marked as a failure.
  static const int maxAttempts = 10;

  /// First retry delay; each subsequent retry multiplies by 4 up to [maxBackoff].
  static const Duration baseBackoff = Duration(seconds: 15);

  /// Ceiling for a single backoff step (~23.7h total across [maxAttempts]).
  static const Duration maxBackoff = Duration(hours: 6);

  /// A `sending` row untouched for longer than this is treated as orphaned
  /// (its isolate died mid-POST) and requeued. Only needs to exceed the request
  /// timeout now that backoff no longer holds the row in `sending`.
  static const Duration staleAfter = Duration(seconds: 150);

  bool _running = false;

  /// Attempts to deliver every due message. Safe to call concurrently within
  /// one isolate (overlaps are ignored); cross-isolate safety comes from the
  /// atomic claim in [_deliver].
  Future<void> flush() async {
    if (_running) return;
    _running = true;
    try {
      final url = settings.webhookUrl;
      if (url == null) return;
      if (!await connectivity.isOnline()) return;

      await repository.reclaimStale(_clock() - staleAfter.inMilliseconds);

      for (final record in await repository.dueForDelivery(_clock())) {
        final delivered = await _deliver(record, url);
        if (!delivered) break; // went offline — stop, resume later
      }

      await notifications.reconcileFailures(await repository.countFailed());
    } finally {
      _running = false;
    }
  }

  /// Sends [record] once. Returns false only when delivery was abandoned
  /// because the device went offline (the record is left queued and due); true
  /// once it reached a terminal state, was rescheduled, was claimed by another
  /// isolate, or was skipped.
  Future<bool> _deliver(SmsRecord record, String url) async {
    if (!await connectivity.isOnline()) return false;

    final id = record.id!;
    // Claim the row; if another isolate already owns it, skip.
    if (!await repository.claim(id, _clock())) return true;

    final result = await client.send(url, record);
    if (result.ok) {
      await repository.updateStatus(
        id,
        SmsStatus.success,
        attempts: record.attempts,
        updatedAt: _clock(),
        nextAttemptAt: null,
      );
      return true;
    }

    // A failure while offline is a transport drop, not a real attempt: release
    // the row unchanged (still due) so the next online flush retries it.
    if (!await connectivity.isOnline()) {
      await repository.updateStatus(
        id,
        SmsStatus.queued,
        attempts: record.attempts,
        updatedAt: _clock(),
        nextAttemptAt: record.nextAttemptAt,
      );
      return false;
    }

    final attempts = record.attempts + 1;
    if (attempts >= maxAttempts) {
      await repository.updateStatus(
        id,
        SmsStatus.failure,
        attempts: attempts,
        lastError: result.error,
        updatedAt: _clock(),
        nextAttemptAt: null,
      );
      return true;
    }

    await repository.updateStatus(
      id,
      SmsStatus.queued,
      attempts: attempts,
      lastError: result.error,
      updatedAt: _clock(),
      nextAttemptAt: _clock() + _backoff(attempts).inMilliseconds,
    );
    return true;
  }

  /// Capped exponential backoff. [attempt] is the already-incremented count, so
  /// attempt 1 -> 15s, 2 -> 1m, 3 -> 4m, ... capped at [maxBackoff].
  Duration _backoff(int attempt) {
    final seconds = min(
      maxBackoff.inSeconds,
      baseBackoff.inSeconds * pow(4, attempt - 1).toInt(),
    );
    return Duration(seconds: seconds);
  }
}
