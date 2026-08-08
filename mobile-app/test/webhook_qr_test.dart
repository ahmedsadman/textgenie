import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/utils/webhook_qr.dart';

void main() {
  group('parseWebhookQr', () {
    const url = 'https://api.example.com/api/webhook/abc-123';

    String envelope(Map<String, dynamic> body) => jsonEncode(body);

    test('returns URL for a valid envelope', () {
      final raw = envelope({'type': webhookQrType, 'url': url});
      expect(parseWebhookQr(raw), url);
    });

    test('returns null when the type marker is missing', () {
      final raw = envelope({'url': url});
      expect(parseWebhookQr(raw), isNull);
    });

    test('returns null when the type marker is wrong', () {
      final raw = envelope({'type': 'something-else', 'url': url});
      expect(parseWebhookQr(raw), isNull);
    });

    test('returns null when the url field is missing', () {
      final raw = envelope({'type': webhookQrType});
      expect(parseWebhookQr(raw), isNull);
    });

    test('returns null when the url is not a string', () {
      final raw = envelope({'type': webhookQrType, 'url': 42});
      expect(parseWebhookQr(raw), isNull);
    });

    test('returns null for malformed JSON', () {
      expect(parseWebhookQr('not-json'), isNull);
      expect(parseWebhookQr(''), isNull);
    });

    test('returns null for a non-http scheme', () {
      final raw = envelope({'type': webhookQrType, 'url': 'ftp://x.example'});
      expect(parseWebhookQr(raw), isNull);
    });

    test('returns null for a URL with an empty host', () {
      final raw = envelope({'type': webhookQrType, 'url': 'http:///path'});
      expect(parseWebhookQr(raw), isNull);
    });

    test('ignores a bare URL string without the envelope', () {
      expect(parseWebhookQr(url), isNull);
    });
  });

  group('validateWebhookUrl', () {
    test('accepts https and http', () {
      expect(validateWebhookUrl('https://example.com/hook'), isNull);
      expect(validateWebhookUrl('http://example.com/hook'), isNull);
    });

    test('rejects empty and malformed', () {
      expect(validateWebhookUrl(null), isNotNull);
      expect(validateWebhookUrl(''), isNotNull);
      expect(validateWebhookUrl('not-a-url'), isNotNull);
    });

    test('rejects unsupported schemes', () {
      expect(validateWebhookUrl('ftp://example.com'), isNotNull);
    });
  });
}
