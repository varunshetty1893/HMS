import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../core/realtime/ws_client.dart';
import '../../models/table_session_detail.dart';
import '../auth/auth_controller.dart';
import '../../core/network/api_exceptions.dart';

final tableDetailControllerProvider = StateNotifierProvider.autoDispose.family<
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
  StreamSubscription<Map<String, dynamic>>? _wsSubscription;

  TableDetailController(this._apiClient, this._wsClient, this.tableId)
      : super(const TableDetailState()) {
    _initWsListener();
    loadSessionDetail();
    // Fallback: refresh periodically so a payment taken at admin shows up.
    _pollTimer = Timer.periodic(
      const Duration(seconds: 8),
      (_) => loadSessionDetail(silent: true),
    );
  }

  Timer? _pollTimer;

  void _initWsListener() {
    _wsSubscription = _wsClient.messages.listen((msg) {
      if (!mounted) return;
      final type = (msg['event'] ?? msg['type'])?.toString();
      if (type != null &&
          (type.startsWith('order.') ||
           type.startsWith('table.') ||
           type.startsWith('bill.') ||
           type.startsWith('waiter.'))) {
        loadSessionDetail(silent: true);
      }
    });
  }

  @override
  void dispose() {
    _wsSubscription?.cancel();
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> loadSessionDetail({bool silent = false}) async {
    if (!mounted) return;
    if (!silent) {
      state = state.copyWith(isLoading: true, error: null);
    }
    try {
      final res =
          await _apiClient.get('/api/v1/waiter/tables/$tableId/session');
      if (!mounted) return;
      final detail = TableSessionDetail.fromJson(res as Map<String, dynamic>);
      state =
          state.copyWith(sessionDetail: detail, isLoading: false, error: null);
    } catch (e) {
      if (!mounted) return;
      if (!silent) {
        state = state.copyWith(isLoading: false, error: describeError(e));
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
      if (!mounted) return false;
      await loadSessionDetail(silent: true);
      return true;
    } catch (e) {
      if (!mounted) return false;
      state = state.copyWith(error: describeError(e));
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
          'force': true,
        },
      );
      if (!mounted) return false;
      await loadSessionDetail(silent: true);
      return true;
    } catch (e) {
      if (!mounted) return false;
      state = state.copyWith(error: describeError(e));
      return false;
    }
  }

  Future<bool> adjustItemPrice({
    required String orderId,
    required String itemId,
    required double newUnitPrice,
    required String reason,
  }) async {
    try {
      await _apiClient.post(
        '/api/v1/waiter/orders/$orderId/items/$itemId/adjust',
        data: {
          'expected_version': _versionOf(orderId),
          'adjustment_type': 'CUSTOM_PRICE',
          'custom_unit_price': newUnitPrice.toStringAsFixed(2),
          'reason': reason,
        },
      );
      if (!mounted) return false;
      await loadSessionDetail(silent: true);
      return true;
    } catch (e) {
      if (!mounted) return false;
      state = state.copyWith(error: describeError(e));
      return false;
    }
  }
}
