import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/realtime/ws_client.dart';
import '../auth/auth_controller.dart';

class WaiterNotification {
  final String id;
  final String eventType;
  final String title;
  final String message;
  final String? orderId;

  const WaiterNotification({
    required this.id,
    required this.eventType,
    required this.title,
    required this.message,
    this.orderId,
  });

  factory WaiterNotification.fromJson(Map<String, dynamic> json) {
    final payload = json['payload_json'] as Map<String, dynamic>? ?? const {};
    return WaiterNotification(
      id: json['id']?.toString() ?? '',
      eventType: json['event_type']?.toString() ?? '',
      title: json['title']?.toString() ?? 'Restaurant update',
      message: json['message']?.toString() ?? '',
      orderId: json['order_id']?.toString() ?? payload['order_id']?.toString(),
    );
  }
}

class WaiterNotificationsState {
  final List<WaiterNotification> items;
  final bool isLoading;

  const WaiterNotificationsState({this.items = const [], this.isLoading = false});

  int get count => items.length;
  String get badgeText => count > 99 ? '99+' : '$count';

  WaiterNotificationsState copyWith({
    List<WaiterNotification>? items,
    bool? isLoading,
  }) => WaiterNotificationsState(
        items: items ?? this.items,
        isLoading: isLoading ?? this.isLoading,
      );
}

final waiterNotificationsControllerProvider = StateNotifierProvider.autoDispose<
    WaiterNotificationsController, WaiterNotificationsState>((ref) {
  final controller = WaiterNotificationsController(
    ref.read(apiClientProvider),
    ref.read(wsClientProvider),
  );
  ref.onDispose(controller.dispose);
  return controller;
});

/// Durable waiter alerts. The server remains the source of truth; WebSocket
/// events only trigger a refresh, so reconnects and duplicate events cannot
/// inflate the badge.
class WaiterNotificationsController extends StateNotifier<WaiterNotificationsState> {
  final ApiClient _api;
  final WsClient _ws;
  StreamSubscription<Map<String, dynamic>>? _events;
  StreamSubscription<bool>? _connection;

  WaiterNotificationsController(this._api, this._ws)
      : super(const WaiterNotificationsState()) {
    _events = _ws.messages.listen((event) {
      final type = (event['event'] ?? event['type'])?.toString();
      if (type == 'order.ready' || type == 'order.modified' || type == 'order.modification_acknowledged') {
        load(silent: true);
      }
    });
    _connection = _ws.isConnectedStream.listen((connected) {
      if (connected) load(silent: true);
    });
    load();
  }

  @override
  void dispose() {
    _events?.cancel();
    _connection?.cancel();
    super.dispose();
  }

  Future<void> load({bool silent = false}) async {
    if (!silent) state = state.copyWith(isLoading: true);
    try {
      final result = await _api.get(
        '/notifications/unread',
        queryParams: const {'channel': 'WAITERS_ALL', 'limit': '100'},
      );
      final raw = result as List? ?? const [];
      final items = raw
          .whereType<Map>()
          .map((item) => WaiterNotification.fromJson(Map<String, dynamic>.from(item)))
          // The badge is deliberately limited to actionable waiter work.
          .where((item) => item.eventType == 'ORDER_READY' || item.eventType == 'ORDER_MODIFIED')
          .toList();
      if (mounted) state = state.copyWith(items: items, isLoading: false);
    } catch (_) {
      if (mounted && !silent) state = state.copyWith(isLoading: false);
    }
  }

  Future<void> acknowledgeAll() async {
    final ids = state.items.map((item) => item.id).where((id) => id.isNotEmpty).toList();
    if (ids.isEmpty) return;
    await _api.post('/notifications/ack', data: {'notification_ids': ids});
    if (mounted) state = state.copyWith(items: const []);
  }
}
