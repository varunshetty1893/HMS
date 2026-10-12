import 'package:flutter_test/flutter_test.dart';
import 'package:kitchen_app/config/env_config.dart';
import 'package:kitchen_app/core/network/api_client.dart';

void main() {
  group('Kitchen App EnvConfig & Network Resolution', () {
    test('Default base URL has /api/v1 prefix', () {
      expect(EnvConfig.apiBaseUrl.endsWith('/api/v1'), isTrue);
    });

    test('resolveUri corrects /auth/login path and prevents duplicate prefixes', () {
      final uri = ApiClient.resolveUri(
        'http://192.168.1.15:8000/api/v1',
        '/auth/login',
      );
      expect(uri.toString(), equals('http://192.168.1.15:8000/api/v1/auth/login'));
    });

    test('resolveUri handles KDS queue endpoint', () {
      final uri = ApiClient.resolveUri(
        'http://10.0.2.2:8000/api/v1',
        '/kitchen/orders/active',
        queryParams: {'status': 'PLACED'},
      );
      expect(uri.toString(), equals('http://10.0.2.2:8000/api/v1/kitchen/orders/active?status=PLACED'));
    });
  });
}
