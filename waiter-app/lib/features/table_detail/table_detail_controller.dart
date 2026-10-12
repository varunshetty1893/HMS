import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../core/realtime/ws_client.dart';
import '../../models/table_session_detail.dart';
import '../auth/auth_controller.dart';

final tableDetailControllerProvider = StateNotifierProvider.family<
    TableDetailController, TableDetailState, String>((ref, tableId) {
  final apiClient = ref.watch(apiClientProvider);
  final wsClient = ref.watch(wsClientProvider);
  return TableDetailController(apiClient, wsClient, tableId);
});

class TableDetailState {
  final bool isLoading;
  final String? error;
  final TableSessionDetail? sessionDetail;

  const TableDetailState({
    this.isLoading = false,
    this.error,
    this.sessionDetail,
  });

  TableDetailState copyWith({
    bool? isLoading,
    String? error,
    TableSessionDetail? sessionDetail,
  }) {
    return TableDetailState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      sessionDetail: sessionDetail ?? this.sessionDetail,
    );
  }
}

class TableDetailController extends StateNotifier<TableDetailState> {
  final ApiClient _apiClient;
  final WsClient _wsClient;
  final String tableId;

  TableDetailController(this._apiClient, this._wsClient, this.tableId)
      : super(const TableDetailState()) {
    _initWsListener();
    loadSessionDetail();
  }

  void _initWsListener() {
    _wsClient.messages.listen((msg) {
      final type = msg['type'] as String?;
      if (type == 'order.created' ||
          type == 'order.status_changed' ||
          type == 'order.modified' ||
          type == 'order.cancelled' ||
          type == 'order.ready' ||
          type == 'order.served' ||
          type == 'table.session_opened' ||
          type == 'table.session_closed') {
        loadSessionDetail(silent: true);
      }
    });
  }

  Future<void> loadSessionDetail({bool silent = false}) async {
    if (!silent) {
      state = state.copyWith(isLoading: true, error: null);
    }
    try {
      final res = await _apiClient.get('/api/v1/waiter/tables/$tableId/session');
      final detail = TableSessionDetail.fromJson(res as Map<String, dynamic>);
      state = state.copyWith(sessionDetail: detail, isLoading: false, error: null);
    } catch (e) {
      if (!silent) {
        state = state.copyWith(isLoading: false, error: e.toString());
      }
    }
  }

  /// Optimistic-concurrency version of an order from the loaded session detail.
  int _versionOf(String orderId) {
    final orders = state.sessionDetail?.activeOrders ?? const [];
    for (final o in orders) {
      if (o.id == orderId) return o.version;
    }
    return 1;
  }

  Future<bool> markOrderServed(String orderId) async {
    try {
      await _apiClient.post(
        '/api/v1/waiter/orders/$orderId/serve',
        data: {'expected_version': _versionOf(orderId)},
      );
      await loadSessionDetail(silent: true);
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> cancelOrder(String orderId, String reason) async {
    try {
      await _apiClient.post(
        '/api/v1/waiter/orders/$orderId/cancel',
        data: {
          'expected_version': _versionOf(orderId),
          'cancellation_reason': reason,
        },
      );
      await loadSessionDetail(silent: true);
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }
}
