import 'dart:async';

import 'package:http/http.dart' as http;

import '../models/sms_record.dart';

/// Result of a single webhook delivery attempt.
class WebhookResult {
  const WebhookResult.success() : ok = true, error = null;
  const WebhookResult.failure(this.error) : ok = false;

  final bool ok;
  final String? error;
}

/// POSTs an [SmsRecord] as JSON to an opaque, user-supplied webhook URL.
class WebhookClient {
  WebhookClient({
    http.Client? client,
    this.timeout = const Duration(seconds: 30),
  }) : _client = client ?? http.Client();

  final http.Client _client;
  final Duration timeout;

  Future<WebhookResult> send(String url, SmsRecord record) async {
    final Uri uri;
    try {
      uri = Uri.parse(url);
    } catch (_) {
      return const WebhookResult.failure('Invalid webhook URL');
    }
    try {
      final response = await _client
          .post(
            uri,
            headers: const {'Content-Type': 'application/json'},
            body: record.toWebhookBody(),
          )
          .timeout(timeout);
      final code = response.statusCode;
      if (code >= 200 && code < 300) {
        return const WebhookResult.success();
      }
      return WebhookResult.failure('HTTP $code');
    } on TimeoutException {
      return const WebhookResult.failure('Request timed out');
    } catch (e) {
      return WebhookResult.failure(e.toString());
    }
  }

  void close() => _client.close();
}
