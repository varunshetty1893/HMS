import 'package:flutter_test/flutter_test.dart';
import 'package:waiter_app/config/env_config.dart';
import 'package:waiter_app/core/network/api_client.dart';

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
}
