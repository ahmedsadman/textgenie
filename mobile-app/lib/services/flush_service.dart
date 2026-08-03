import 'dart:async';
import 'dart:math';

import '../data/settings_repository.dart';
import '../data/sms_repository.dart';
import '../models/sms_record.dart';
import 'connectivity_service.dart';
import 'webhook_client.dart';

/// Drains the queue to the webhook, one message at a time, with retry/backoff
/// and connectivity gating.
class FlushService {
  FlushService({
    required this.repository,
    required this.client,
    required this.connectivity,
    required this.settings,
    int Function()? clock,
    Future<void> Function(Duration)? sleep,
  }) : _clock = clock ?? (() => DateTime.now().millisecondsSinceEpoch),
       _sleep = sleep ?? Future<void>.delayed;

  final SmsRepository repository;
  final WebhookClient client;
  final ConnectivityService connectivity;
  final SettingsRepository settings;
  final int Function() _clock;
  final Future<void> Function(Duration) _sleep;

  /// Max delivery attempts before a record is marked as a failure.
  static const int maxAttempts = 5;

  /// Backoff cap so an offline stretch never parks a retry for too long.
  static const Duration maxBackoff = Duration(seconds: 60);

  /// A `sending` row untouched for longer than this is treated as orphaned
  /// (its isolate died) and requeued. Must exceed one backoff + request cycle.
  static const Duration staleAfter = Duration(seconds: 150);

  bool _running = false;

  /// Attempts to deliver every queued message. Safe to call concurrently within
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

      for (final record in await repository.queued()) {
        final delivered = await _deliver(record, url);
        if (!delivered) break; // went offline — stop, resume later
      }
    } finally {
      _running = false;
    }
  }

  /// Returns false when delivery was abandoned because the device went offline
  /// (the record is left queued); true once it reached a terminal state, was
  /// claimed by another isolate, or was skipped.
  Future<bool> _deliver(SmsRecord record, String url) async {
    if (!await connectivity.isOnline()) return false;

    final id = record.id!;
    // Claim the row; if another isolate already owns it, skip.
    if (!await repository.claim(id, _clock())) return true;

    var attempts = record.attempts;
    while (true) {
      final result = await client.send(url, record);
      if (result.ok) {
        await repository.updateStatus(
          id,
          SmsStatus.success,
          attempts: attempts,
          updatedAt: _clock(),
        );
        return true;
      }

      attempts++;
      if (attempts >= maxAttempts) {
        await repository.updateStatus(
          id,
          SmsStatus.failure,
          attempts: attempts,
          lastError: result.error,
          updatedAt: _clock(),
        );
        return true;
      }

      // Keep the row owned (status stays `sending`) while backing off, so no
      // other isolate can grab it; persist progress for resume after a crash.
      await repository.updateStatus(
        id,
        SmsStatus.sending,
        attempts: attempts,
        lastError: result.error,
        updatedAt: _clock(),
      );
      await _sleep(_backoff(attempts));

      if (!await connectivity.isOnline()) {
        await repository.updateStatus(
          id,
          SmsStatus.queued,
          attempts: attempts,
          updatedAt: _clock(),
        );
        return false;
      }
    }
  }

  Duration _backoff(int attempt) {
    final seconds = min(maxBackoff.inSeconds, pow(2, attempt).toInt());
    return Duration(seconds: seconds);
  }
}
