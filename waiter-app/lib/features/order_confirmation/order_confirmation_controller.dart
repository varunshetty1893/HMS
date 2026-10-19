import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../core/network/api_exceptions.dart';
import '../../core/realtime/ws_client.dart';
import '../../models/order_model.dart';

/// QR orders waiting for a waiter to confirm that guests are really seated (threat T-01).
final orderConfirmationControllerProvider = StateNotifierProvider<
    OrderConfirmationController, OrderConfirmationState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final wsClient = ref.watch(wsClientProvider);
  return OrderConfirmationController(apiClient, wsClient);
});

class PendingConfirmation {
  final OrderModel order;
  final String tableLabel;

  /// Local deadline, derived from the server's `seconds_remaining` so a wrong
  /// phone clock cannot show a wrong countdown.
  final DateTime expiresAt;

  const PendingConfirmation({
    required this.order,
    required this.tableLabel,
    required this.expiresAt,
  });

  factory PendingConfirmation.fromJson(Map<String, dynamic> json) {
    final orderJson = json['order'] as Map<String, dynamic>;
    final order = OrderModel.fromJson(orderJson);
    final seconds = (json['seconds_remaining'] as num?)?.toInt() ?? 0;
    final label = orderJson['table_display_name']?.toString() ??
        (order.tableNumber != null ? 'Table ${order.tableNumber}' : 'Table');
    return PendingConfirmation(
      order: order,
      tableLabel: label,
      expiresAt: DateTime.now().add(Duration(seconds: seconds)),
    );
  }
}

class OrderConfirmationState {
  final bool isLoading;
  final String? error;
  final List<PendingConfirmation> items;
  final Set<String> busyIds;
  final DateTime now;

  OrderConfirmationState({
    this.isLoading = false,
    this.error,
    this.items = const [],
    this.busyIds = const {},
    DateTime? now,
  }) : now = now ?? DateTime.now();

  int get count => items.length;

  int secondsLeft(PendingConfirmation item) {
    final left = item.expiresAt.difference(now).inSeconds;
    return left < 0 ? 0 : left;
  }

  OrderConfirmationState copyWith({
    bool? isLoading,
    String? error,
    bool clearError = false,
    List<PendingConfirmation>? items,
    Set<String>? busyIds,
    DateTime? now,
  }) {
    return OrderConfirmationState(
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      items: items ?? this.items,
      busyIds: busyIds ?? this.busyIds,
      now: now ?? this.now,
    );
  }
}

class OrderConfirmationController extends StateNotifier<OrderConfirmationState> {
  final ApiClient _apiClient;
  final WsClient _wsClient;
  StreamSubscription<Map<String, dynamic>>? _wsSub;
  Timer? _ticker;

  OrderConfirmationController(this._apiClient, this._wsClient)
      : super(OrderConfirmationState()) {
    _wsSub = _wsClient.messages.listen((msg) {
      final type = (msg['event'] ?? msg['type'])?.toString();
      if (type == 'order.confirmation_requested' ||
          type == 'order.confirmation_resolved') {
        load(silent: true);
      }
    });
    // 1s tick keeps the countdown live; reload once a request runs out so the
    // list matches what the server auto-cancelled.
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (state.items.isEmpty) return;
      final expiredNow = state.items.any((i) => state.secondsLeft(i) == 0);
      state = state.copyWith(now: DateTime.now());
      if (expiredNow) load(silent: true);
    });
    load();
  }

  Future<void> load({bool silent = false}) async {
    if (!silent) state = state.copyWith(isLoading: true, clearError: true);
    try {
      final res = await _apiClient.get('/api/v1/waiter/order-confirmations');
      final raw = (res is Map ? res['items'] : null) as List? ?? const [];
      final items = raw
          .map((e) => PendingConfirmation.fromJson(e as Map<String, dynamic>))
          .toList();
      state = state.copyWith(
        items: items,
        isLoading: false,
        now: DateTime.now(),
        clearError: silent ? false : true,
      );
    } catch (e) {
      if (!silent) {
        state = state.copyWith(isLoading: false, error: describeError(e));
      }
    }
  }

  /// Guests are seated: release the order to the kitchen.
  Future<bool> confirm(String orderId) => _resolve(orderId, 'confirm', null);

  /// Nobody is at the table: reject the request.
  Future<bool> reject(String orderId, {String? reason}) =>
      _resolve(orderId, 'reject', reason);

  Future<bool> _resolve(String orderId, String action, String? reason) async {
    if (state.busyIds.contains(orderId)) return false;
    state = state.copyWith(
      busyIds: {...state.busyIds, orderId},
      clearError: true,
    );
    try {
      await _apiClient.post(
        '/api/v1/waiter/orders/$orderId/$action',
        data: reason == null || reason.trim().isEmpty
            ? <String, dynamic>{}
            : {'reason': reason.trim()},
      );
      state = state.copyWith(
        items: state.items.where((i) => i.order.id != orderId).toList(),
        busyIds: {...state.busyIds}..remove(orderId),
      );
      return true;
    } catch (e) {
      // Already handled by another waiter, expired, or over the table limit:
      // show the reason and re-sync the list.
      state = state.copyWith(
        error: describeError(e),
        busyIds: {...state.busyIds}..remove(orderId),
      );
      await load(silent: true);
      return false;
    }
  }

  @override
  void dispose() {
    _ticker?.cancel();
    _wsSub?.cancel();
    super.dispose();
  }
}
