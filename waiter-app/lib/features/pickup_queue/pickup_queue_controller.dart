import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../core/realtime/ws_client.dart';
import '../../models/order_model.dart';
import '../auth/auth_controller.dart';

final pickupQueueControllerProvider =
    StateNotifierProvider<PickupQueueController, PickupQueueState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final wsClient = ref.watch(wsClientProvider);
  return PickupQueueController(apiClient, wsClient);
});

class PickupQueueState {
  final bool isLoading;
  final String? error;
  final List<OrderModel> readyOrders;
  final Set<String> markingServedIds;

  const PickupQueueState({
    this.isLoading = false,
    this.error,
    this.readyOrders = const [],
    this.markingServedIds = const {},
  });

  PickupQueueState copyWith({
    bool? isLoading,
    String? error,
    List<OrderModel>? readyOrders,
    Set<String>? markingServedIds,
  }) {
    return PickupQueueState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      readyOrders: readyOrders ?? this.readyOrders,
      markingServedIds: markingServedIds ?? this.markingServedIds,
    );
  }
}

class PickupQueueController extends StateNotifier<PickupQueueState> {
  final ApiClient _apiClient;
  final WsClient _wsClient;

  PickupQueueController(this._apiClient, this._wsClient)
      : super(const PickupQueueState()) {
    _initWsListener();
    loadReadyOrders();
  }

  void _initWsListener() {
    _wsClient.messages.listen((msg) {
      final type = msg['type'] as String?;
      if (type == 'order.ready' || type == 'order.served') {
        loadReadyOrders(silent: true);
      }
    });
  }

  Future<void> loadReadyOrders({bool silent = false}) async {
    if (!silent) state = state.copyWith(isLoading: true, error: null);
    try {
      final res = await _apiClient
          .get('/api/v1/waiter/orders/active?status=READY');
      final List<OrderModel> orders;
      if (res is List) {
        orders = res
            .map((e) => OrderModel.fromJson(e as Map<String, dynamic>))
            .toList();
      } else if (res is Map && res['orders'] != null) {
        orders = (res['orders'] as List)
            .map((e) => OrderModel.fromJson(e as Map<String, dynamic>))
            .toList();
      } else {
        orders = [];
      }
      state = state.copyWith(
          readyOrders: orders, isLoading: false, error: null);
    } catch (e) {
      if (!silent) {
        state = state.copyWith(isLoading: false, error: e.toString());
      }
    }
  }

  Future<void> markServed(String orderId) async {
    final newMarking = Set<String>.from(state.markingServedIds)..add(orderId);
    state = state.copyWith(markingServedIds: newMarking);
    try {
      final version = state.readyOrders
          .firstWhere((o) => o.id == orderId, orElse: () => state.readyOrders.first)
          .version;
      await _apiClient.post(
        '/api/v1/waiter/orders/$orderId/serve',
        data: {'expected_version': version},
      );
      // Remove served order from list immediately for snappy UX
      final updated =
          state.readyOrders.where((o) => o.id != orderId).toList();
      final newMarking2 = Set<String>.from(state.markingServedIds)
        ..remove(orderId);
      state =
          state.copyWith(readyOrders: updated, markingServedIds: newMarking2);
    } catch (e) {
      final newMarking2 = Set<String>.from(state.markingServedIds)
        ..remove(orderId);
      state = state.copyWith(
          error: e.toString(), markingServedIds: newMarking2);
    }
  }
}
