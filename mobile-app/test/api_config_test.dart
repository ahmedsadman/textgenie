import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/utils/api_config.dart';

void main() {
  test('parses base URL and token from a standard webhook URL', () {
    final config = parseWebhookUrl(
      'https://host.example.com/api/webhook/abc123',
    );
    expect(config, isNotNull);
    expect(config!.baseUrl, 'https://host.example.com/api');
    expect(config.token, 'abc123');
  });

  test('preserves a non-default port', () {
    final config = parseWebhookUrl('http://localhost:8001/api/webhook/tok');
    expect(config!.baseUrl, 'http://localhost:8001/api');
    expect(config.token, 'tok');
  });

  test('ignores a trailing slash after the token', () {
    final config = parseWebhookUrl('https://host/api/webhook/tok/');
    expect(config!.token, 'tok');
    expect(config.baseUrl, 'https://host/api');
  });

  test('handles a webhook mounted at the host root', () {
    final config = parseWebhookUrl('https://host/webhook/tok');
    expect(config!.baseUrl, 'https://host');
    expect(config.token, 'tok');
  });

  test('returns null for null, empty, or whitespace', () {
    expect(parseWebhookUrl(null), isNull);
    expect(parseWebhookUrl(''), isNull);
    expect(parseWebhookUrl('   '), isNull);
  });

  test('returns null when there is no webhook segment', () {
    expect(parseWebhookUrl('https://host/api/banks'), isNull);
  });

  test('returns null when the token is missing', () {
    expect(parseWebhookUrl('https://host/api/webhook/'), isNull);
    expect(parseWebhookUrl('https://host/api/webhook'), isNull);
  });

  test('returns null for a non-absolute URL', () {
    expect(parseWebhookUrl('api/webhook/tok'), isNull);
  });
}
