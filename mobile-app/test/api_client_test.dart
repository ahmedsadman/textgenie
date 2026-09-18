import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:mocktail/mocktail.dart';
import 'package:textgenie/services/api_client.dart';
import 'package:textgenie/services/connectivity_service.dart';
import 'package:textgenie/utils/api_config.dart';

class MockHttpClient extends Mock implements http.Client {}

class MockConnectivity extends Mock implements ConnectivityService {}

void main() {
  const config = ApiConfig(baseUrl: 'https://host/api', token: 'secret-token');

  late MockHttpClient http_;
  late MockConnectivity connectivity;
  late ApiClient client;

  setUpAll(() {
    registerFallbackValue(Uri.parse('https://x'));
  });

  setUp(() {
    http_ = MockHttpClient();
    connectivity = MockConnectivity();
    client = ApiClient(client: http_, connectivity: connectivity);
    when(() => connectivity.isOnline()).thenAnswer((_) async => true);
  });

  void stubResponse(String body, int status) {
    when(
      () => http_.get(any(), headers: any(named: 'headers')),
    ).thenAnswer((_) async => http.Response(body, status));
  }

  test('sends the bearer token and returns decoded JSON', () async {
    stubResponse('{"currency":"BDT"}', 200);

    final result = await client.get(config, '/settings/currency');
    expect(result, {'currency': 'BDT'});

    final captured = verify(
      () => http_.get(captureAny(), headers: captureAny(named: 'headers')),
    ).captured;
    final uri = captured[0] as Uri;
    final headers = captured[1] as Map<String, String>;
    expect(uri.toString(), 'https://host/api/settings/currency');
    expect(headers['Authorization'], 'Bearer secret-token');
  });

  test('throws network without calling http when offline', () async {
    when(() => connectivity.isOnline()).thenAnswer((_) async => false);

    await expectLater(
      client.get(config, '/banks'),
      throwsA(
        isA<ApiException>().having((e) => e.kind, 'kind', ApiErrorKind.network),
      ),
    );
    verifyNever(() => http_.get(any(), headers: any(named: 'headers')));
  });

  test('maps 401 to unauthorized', () async {
    stubResponse('nope', 401);
    await expectLater(
      client.get(config, '/banks'),
      throwsA(
        isA<ApiException>().having(
          (e) => e.kind,
          'kind',
          ApiErrorKind.unauthorized,
        ),
      ),
    );
  });

  test('maps other non-2xx to http with the status code', () async {
    stubResponse('boom', 500);
    await expectLater(
      client.get(config, '/banks'),
      throwsA(
        isA<ApiException>()
            .having((e) => e.kind, 'kind', ApiErrorKind.http)
            .having((e) => e.statusCode, 'statusCode', 500),
      ),
    );
  });

  test('maps invalid JSON to parse', () async {
    stubResponse('not json', 200);
    await expectLater(
      client.get(config, '/banks'),
      throwsA(
        isA<ApiException>().having((e) => e.kind, 'kind', ApiErrorKind.parse),
      ),
    );
  });

  test('maps timeouts and socket errors to network', () async {
    when(
      () => http_.get(any(), headers: any(named: 'headers')),
    ).thenThrow(TimeoutException('slow'));
    await expectLater(
      client.get(config, '/banks'),
      throwsA(
        isA<ApiException>().having((e) => e.kind, 'kind', ApiErrorKind.network),
      ),
    );

    when(
      () => http_.get(any(), headers: any(named: 'headers')),
    ).thenThrow(const SocketException('down'));
    await expectLater(
      client.get(config, '/banks'),
      throwsA(
        isA<ApiException>().having((e) => e.kind, 'kind', ApiErrorKind.network),
      ),
    );
  });

  test('encodes list query params as repeated keys', () async {
    stubResponse('{}', 200);
    await client.get(
      config,
      '/transactions',
      query: {
        'page': 1,
        'types': ['income', 'expense'],
      },
    );

    final uri =
        verify(
              () => http_.get(captureAny(), headers: any(named: 'headers')),
            ).captured.single
            as Uri;
    expect(uri.queryParametersAll['types'], ['income', 'expense']);
    expect(uri.queryParameters['page'], '1');
  });
}
