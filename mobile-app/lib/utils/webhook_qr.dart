import 'dart:convert';

const String webhookQrType = 'textgenie-webhook';

/// Validates a webhook URL. Returns an error message if invalid, else null.
String? validateWebhookUrl(String? value) {
  final text = value?.trim() ?? '';
  if (text.isEmpty) return 'Webhook URL is required';
  final uri = Uri.tryParse(text);
  if (uri == null || !uri.isAbsolute || !uri.hasScheme || uri.host.isEmpty) {
    return 'Enter a valid URL (including https://)';
  }
  if (uri.scheme != 'http' && uri.scheme != 'https') {
    return 'URL must start with http:// or https://';
  }
  return null;
}

/// Parses a QR payload emitted by the TextGenie web dashboard.
///
/// Expects the JSON envelope `{"type":"textgenie-webhook","url":"..."}`.
/// Returns the trimmed URL if the envelope is valid and the URL passes
/// [validateWebhookUrl]; otherwise null (unrelated QR codes are silently
/// ignored so the scanner can keep looking).
String? parseWebhookQr(String raw) {
  final trimmed = raw.trim();
  if (trimmed.isEmpty) return null;
  final dynamic decoded;
  try {
    decoded = jsonDecode(trimmed);
  } catch (_) {
    return null;
  }
  if (decoded is! Map) return null;
  if (decoded['type'] != webhookQrType) return null;
  final url = decoded['url'];
  if (url is! String) return null;
  if (validateWebhookUrl(url) != null) return null;
  return url.trim();
}
