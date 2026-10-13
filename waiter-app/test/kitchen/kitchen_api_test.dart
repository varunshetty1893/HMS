import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:waiter_app/core/network/api_client.dart';
import 'package:waiter_app/core/network/api_exceptions.dart';
import 'package:waiter_app/kitchen/data/kitchen_api.dart';

import '../helpers/fakes.dart';

Future<(KitchenApi, List<http.Request>)> _api(
  Future<http.Response> Function(http.Request) handler,
) async {
  final requests = <http.Request>[];
  final storage = InMemoryTokenStorage();
  await storage.saveAuth(
    accessToken: 'kitchen_token',
    userId: 'u-2',
    username: 'chef1',
    fullName: 'Chef One',
    role: 'KITCHEN',
  );
  final client = MockClient((req) {
    requests.add(req);
    return handler(req);
  });
  return (KitchenApi(ApiClient(httpClient: client, tokenStorage: storage)), requests);
}

void main() {
  group('KitchenApi (shared ApiClient, /api/v1 never duplicated)', () {
    test('resolveUri handles KDS queue endpoint', () {
      final uri = ApiClient.resolveUri(
        'http://10.0.2.2:8000/api/v1',
        '/kitchen/orders/active',
        queryParams: {'status': 'PLACED'},
      );
      expect(uri.toString(),
          'http://10.0.2.2:8000/api/v1/kitchen/orders/active?status=PLACED');
    });

    test('getActiveQueue GETs /kitchen/orders/active with the bearer token', () async {
      final (api, requests) = await _api(
        (req) async => jsonResponse({'counts': {}, 'orders': []}, 200),
      );

      final data = await api.getActiveQueue(statusFilter: 'PLACED');

      expect(data['orders'], isEmpty);
      expect(requests.single.method, 'GET');
      expect(requests.single.url.path, '/api/v1/kitchen/orders/active');
      expect(requests.single.url.queryParameters['status'], 'PLACED');
      expect(requests.single.headers['Authorization'], 'Bearer kitchen_token');
    });

    test('markOrderReady POSTs expected_version', () async {
      final (api, requests) =
          await _api((req) async => jsonResponse({'id': 'o1'}, 200));

      await api.markOrderReady('o1', 3);

      expect(requests.single.method, 'POST');
      expect(requests.single.url.path, '/api/v1/kitchen/orders/o1/ready');
      expect(jsonDecode(requests.single.body), {'expected_version': 3});
    });

    test('rejectOrder POSTs version and reason', () async {
      final (api, requests) =
          await _api((req) async => jsonResponse({'id': 'o1'}, 200));

      await api.rejectOrder('o1', 2, 'Out of stock');

      expect(requests.single.url.path, '/api/v1/kitchen/orders/o1/reject');
      expect(jsonDecode(requests.single.body),
          {'expected_version': 2, 'reason': 'Out of stock'});
    });

    test('getOrderHistory sends paging params', () async {
      final (api, requests) = await _api((req) async => jsonResponse([], 200));

      final history = await api.getOrderHistory(page: 2, pageSize: 30);

      expect(history, isEmpty);
      expect(requests.single.url.path, '/api/v1/kitchen/orders/history');
      expect(requests.single.url.queryParameters, {'page': '2', 'page_size': '30'});
    });

    test('409 surfaces as ConflictException (board refreshes the ticket)', () async {
      final (api, _) = await _api((req) async => jsonResponse({
            'error': {'code': 'ORDER_VERSION_CONFLICT', 'message': 'stale'},
          }, 409));

      expect(api.acceptOrder('o1', 1), throwsA(isA<ConflictException>()));
    });

    test('403 from the backend is surfaced, not swallowed (waiter token on kitchen route)',
        () async {
      final (api, _) = await _api((req) async => jsonResponse({
            'error': {'code': 'FORBIDDEN', 'message': 'Insufficient role'},
          }, 403));

      expect(
        api.getActiveQueue(),
        throwsA(isA<ApiException>().having((e) => e.code, 'code', 'FORBIDDEN')),
      );
    });
  });
}
