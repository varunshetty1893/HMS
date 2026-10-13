import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../features/auth/auth_controller.dart' show apiClientProvider;

/// Kitchen (`/kitchen/*`) endpoints, built on the app's single [ApiClient] so
/// the base URL, token handling, refresh and `/api/v1` de-duplication are
/// shared with the rest of the app.
///
/// Authorization stays on the backend: these routes require the KITCHEN (or
/// ADMIN) role, so a Waiter token is rejected by the server regardless of
/// what the UI does.
class KitchenApi {
  final ApiClient _client;

  KitchenApi(this._client);

  Future<Map<String, dynamic>> getActiveQueue({String? statusFilter}) async {
    final res = await _client.get(
      '/kitchen/orders/active',
      queryParams: statusFilter != null ? {'status': statusFilter} : null,
    );
    return res as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> acceptOrder(
          String orderId, int expectedVersion) async =>
      await _client.post('/kitchen/orders/$orderId/accept',
          body: {'expected_version': expectedVersion}) as Map<String, dynamic>;

  Future<Map<String, dynamic>> rejectOrder(
    String orderId,
    int expectedVersion,
    String reason,
  ) async =>
      await _client.post('/kitchen/orders/$orderId/reject', body: {
        'expected_version': expectedVersion,
        'reason': reason,
      }) as Map<String, dynamic>;

  Future<Map<String, dynamic>> startPreparingOrder(
          String orderId, int expectedVersion) async =>
      await _client.post('/kitchen/orders/$orderId/preparing',
          body: {'expected_version': expectedVersion}) as Map<String, dynamic>;

  Future<Map<String, dynamic>> markOrderReady(
          String orderId, int expectedVersion) async =>
      await _client.post('/kitchen/orders/$orderId/ready',
          body: {'expected_version': expectedVersion}) as Map<String, dynamic>;

  Future<Map<String, dynamic>> acknowledgeModifications(String orderId) async =>
      await _client.post('/kitchen/orders/$orderId/acknowledge-modifications',
          body: <String, dynamic>{}) as Map<String, dynamic>;

  Future<List<dynamic>> getOrderHistory({int page = 1, int pageSize = 20}) async {
    final res = await _client.get(
      '/kitchen/orders/history',
      queryParams: {
        'page': page.toString(),
        'page_size': pageSize.toString(),
      },
    );
    return res as List<dynamic>;
  }
}

final kitchenApiProvider =
    Provider<KitchenApi>((ref) => KitchenApi(ref.watch(apiClientProvider)));
