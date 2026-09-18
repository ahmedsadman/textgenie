/// Backend connection derived from the saved webhook URL: the API base URL and
/// the per-user token (which doubles as a read-only API key).
class ApiConfig {
  const ApiConfig({required this.baseUrl, required this.token});

  /// e.g. `https://host/api` (no trailing slash).
  final String baseUrl;
  final String token;
}

/// Derives an [ApiConfig] from a webhook URL of the shape
/// `https://host/api/webhook/<token>`. The API base is everything up to the
/// `webhook` path segment; the token is the segment after it.
///
/// Returns null when the URL is empty, malformed, or has no `webhook/<token>`.
ApiConfig? parseWebhookUrl(String? webhookUrl) {
  final raw = webhookUrl?.trim();
  if (raw == null || raw.isEmpty) return null;

  final uri = Uri.tryParse(raw);
  if (uri == null || !uri.isAbsolute || uri.host.isEmpty) return null;

  final segments = uri.pathSegments;
  final webhookIndex = segments.indexOf('webhook');
  if (webhookIndex < 0 || webhookIndex + 1 >= segments.length) return null;

  final token = segments[webhookIndex + 1].trim();
  if (token.isEmpty) return null;

  final basePath = segments.sublist(0, webhookIndex).join('/');
  final base = Uri(
    scheme: uri.scheme,
    host: uri.host,
    port: uri.hasPort ? uri.port : null,
    path: basePath.isEmpty ? '' : '/$basePath',
  ).toString();

  return ApiConfig(baseUrl: base, token: token);
}
