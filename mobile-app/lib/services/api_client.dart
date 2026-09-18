import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../utils/api_config.dart';
import 'connectivity_service.dart';

/// Categories of failure surfaced by [ApiClient].
enum ApiErrorKind {
  /// Offline, timeout, or a socket-level failure.
  network,

  /// 401/403 — bad or missing token.
  unauthorized,

  /// Any other non-2xx HTTP status.
  http,

  /// Response body was not valid JSON.
  parse,
}

class ApiException implements Exception {
  const ApiException(this.kind, {this.statusCode, this.message});

  final ApiErrorKind kind;
  final int? statusCode;
  final String? message;

  factory ApiException.network([String? message]) =>
      ApiException(ApiErrorKind.network, message: message);
  factory ApiException.unauthorized([String? message]) =>
      ApiException(ApiErrorKind.unauthorized, message: message);
  factory ApiException.http(int statusCode) =>
      ApiException(ApiErrorKind.http, statusCode: statusCode);
  factory ApiException.parse([String? message]) =>
      ApiException(ApiErrorKind.parse, message: message);

  @override
  String toString() =>
      'ApiException(${kind.name}, status: $statusCode, message: $message)';
}

/// A thin authenticated GET client for the TextGenie backend. Injects the
/// `Authorization: Bearer <token>` header and maps failures to [ApiException].
class ApiClient {
  ApiClient({
    http.Client? client,
    required this._connectivity,
    this.timeout = const Duration(seconds: 20),
  }) : _client = client ?? http.Client();

  final http.Client _client;
  final ConnectivityService _connectivity;
  final Duration timeout;

  /// Performs an authenticated GET and returns the decoded JSON body.
  Future<Object?> get(
    ApiConfig config,
    String path, {
    Map<String, dynamic>? query,
  }) async {
    if (!await _connectivity.isOnline()) {
      throw ApiException.network('offline');
    }

    final uri = Uri.parse(
      '${config.baseUrl}$path',
    ).replace(queryParameters: _stringifyQuery(query));

    final http.Response response;
    try {
      response = await _client
          .get(
            uri,
            headers: {
              'Authorization': 'Bearer ${config.token}',
              'Accept': 'application/json',
            },
          )
          .timeout(timeout);
    } on TimeoutException {
      throw ApiException.network('timeout');
    } on SocketException {
      throw ApiException.network('socket');
    } catch (e) {
      throw ApiException.network(e.toString());
    }

    final code = response.statusCode;
    if (code == 401 || code == 403) throw ApiException.unauthorized();
    if (code < 200 || code >= 300) throw ApiException.http(code);

    try {
      return jsonDecode(response.body);
    } catch (_) {
      throw ApiException.parse();
    }
  }

  /// Coerces query values to strings; list values become repeated params
  /// (`types=income&types=expense`). Null values are dropped.
  Map<String, dynamic>? _stringifyQuery(Map<String, dynamic>? query) {
    if (query == null) return null;
    final out = <String, dynamic>{};
    query.forEach((key, value) {
      if (value == null) return;
      if (value is Iterable) {
        out[key] = value.map((e) => e.toString()).toList();
      } else {
        out[key] = value.toString();
      }
    });
    return out.isEmpty ? null : out;
  }

  void close() => _client.close();
}
