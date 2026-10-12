import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:waiter_app/config/env_config.dart';
import 'package:waiter_app/core/network/api_client.dart';
import 'package:waiter_app/core/network/api_exceptions.dart';
import 'package:waiter_app/core/realtime/ws_client.dart';
import 'package:waiter_app/core/storage/secure_token_storage.dart';
import 'package:waiter_app/features/auth/auth_controller.dart';

void main() {
  group('EnvConfig & Base URL Selection', () {
    test('Default base URL ends with /api/v1', () {
      final baseUrl = EnvConfig.apiBaseUrl;
      expect(baseUrl.endsWith('/api/v1'), isTrue);
      expect(baseUrl.startsWith('http://'), isTrue);
    });

    test('Default wsUrl ends with /api/v1/ws', () {
      final wsUrl = EnvConfig.wsUrl;
      expect(wsUrl.endsWith('/api/v1/ws'), isTrue);
      expect(wsUrl.startsWith('ws://'), isTrue);
    });

    test('defaultHost is non-empty', () {
      expect(EnvConfig.defaultHost.isNotEmpty, isTrue);
      expect(EnvConfig.apiHost.isNotEmpty, isTrue);
    });
  });

  group('URI Resolution & /api/v1 Deduplication', () {
    test('Prevents duplicated /api/v1 when both baseUrl and path contain it', () {
      final uri = ApiClient.resolveUri(
        'http://10.0.2.2:8000/api/v1',
        '/api/v1/auth/login',
      );
      expect(uri.toString(), equals('http://10.0.2.2:8000/api/v1/auth/login'));
      expect(uri.path, equals('/api/v1/auth/login'));
    });

    test('Composes cleanly when baseUrl has /api/v1 and path is /auth/login', () {
      final uri = ApiClient.resolveUri(
        'http://10.0.2.2:8000/api/v1',
        '/auth/login',
      );
      expect(uri.toString(), equals('http://10.0.2.2:8000/api/v1/auth/login'));
      expect(uri.path, equals('/api/v1/auth/login'));
    });

    test('Works when baseUrl has physical LAN IP with /api/v1', () {
      final uri = ApiClient.resolveUri(
        'http://192.168.1.105:8000/api/v1',
        '/api/v1/auth/login',
      );
      expect(uri.toString(), equals('http://192.168.1.105:8000/api/v1/auth/login'));
    });

    test('Supplies /api/v1 if baseUrl is raw host without prefix', () {
      final uri = ApiClient.resolveUri(
        'http://192.168.1.105:8000',
        '/auth/login',
      );
      expect(uri.toString(), equals('http://192.168.1.105:8000/api/v1/auth/login'));
    });

    test('Retains /api/v1 if baseUrl is raw host and path has /api/v1', () {
      final uri = ApiClient.resolveUri(
        'http://192.168.1.105:8000',
        '/api/v1/waiter/tables',
      );
      expect(uri.toString(), equals('http://192.168.1.105:8000/api/v1/waiter/tables'));
    });

    test('Handles trailing slash on baseUrl and missing leading slash on path', () {
      final uri = ApiClient.resolveUri(
        'http://192.168.1.105:8000/api/v1/',
        'auth/login',
      );
      expect(uri.toString(), equals('http://192.168.1.105:8000/api/v1/auth/login'));
    });

    test('Preserves query parameters correctly', () {
      final uri = ApiClient.resolveUri(
        'http://10.0.2.2:8000/api/v1',
        '/waiter/orders/active',
        queryParams: {'status': 'READY'},
      );
      expect(uri.toString(), equals('http://10.0.2.2:8000/api/v1/waiter/orders/active?status=READY'));
      expect(uri.queryParameters['status'], equals('READY'));
    });
  });

  group('Authentication Controller & Network Error Handling', () {
    test('Successful login sets authenticated state with WAITER user', () async {
      final mockClient = MockClient((request) async {
        // Assert that request path is exactly /api/v1/auth/login (no duplication)
        expect(request.url.path, equals('/api/v1/auth/login'));

        final body = jsonDecode(request.body);
        expect(body['username'], equals('waiter1'));
        expect(body['password'], equals('password123'));

        return http.Response(
          jsonEncode({
            'access_token': 'test_access_jwt',
            'refresh_token': 'test_refresh_jwt',
            'user': {
              'id': 'u-001',
              'username': 'waiter1',
              'full_name': 'Ramesh Kumar',
              'role': 'WAITER',
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final apiClient = ApiClient(httpClient: mockClient);
      final tokenStorage = SecureTokenStorage();
      final wsClient = WsClient();

      final controller = AuthController(
        apiClient: apiClient,
        tokenStorage: tokenStorage,
        wsClient: wsClient,
      );

      final ok = await controller.login('waiter1', 'password123');
      expect(ok, isTrue);
      expect(controller.state.isAuthenticated, isTrue);
      expect(controller.state.user?.role, equals('WAITER'));
      expect(controller.state.user?.username, equals('waiter1'));
      expect(controller.state.error, isNull);
    });

    test('Login rejects unauthorized non-waiter role (e.g. KITCHEN)', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'access_token': 'test_jwt',
            'user': {
              'id': 'u-002',
              'username': 'chef1',
              'full_name': 'Chef Chef',
              'role': 'KITCHEN',
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final controller = AuthController(
        apiClient: ApiClient(httpClient: mockClient),
        tokenStorage: SecureTokenStorage(),
        wsClient: WsClient(),
      );

      final ok = await controller.login('chef1', 'password');
      expect(ok, isFalse);
      expect(controller.state.isAuthenticated, isFalse);
      expect(controller.state.error, contains('Waiter or Admin role required'));
    });

    test('HTTP 401 raises AuthException and sets controller error', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'error': {
              'code': 'INVALID_CREDENTIALS',
              'message': 'Invalid username or password',
            },
          }),
          401,
          headers: {'content-type': 'application/json'},
        );
      });

      final controller = AuthController(
        apiClient: ApiClient(httpClient: mockClient),
        tokenStorage: SecureTokenStorage(),
        wsClient: WsClient(),
      );

      final ok = await controller.login('waiter1', 'wrongpass');
      expect(ok, isFalse);
      expect(controller.state.isAuthenticated, isFalse);
      expect(controller.state.error, contains('Invalid username or password'));
    });

    test('Network timeout / connection failure sets friendly error message', () async {
      final mockClient = MockClient((request) async {
        throw http.ClientException(
          'Connection timed out (OS Error: Connection timed out, errno = 110)',
          request.url,
        );
      });

      final controller = AuthController(
        apiClient: ApiClient(httpClient: mockClient),
        tokenStorage: SecureTokenStorage(),
        wsClient: WsClient(),
      );

      final ok = await controller.login('waiter1', 'secret');
      expect(ok, isFalse);
      expect(controller.state.isAuthenticated, isFalse);
      expect(controller.state.error, contains('Connection timed out'));
    });
  });
}
