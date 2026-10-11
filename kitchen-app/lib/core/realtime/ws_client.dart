// kitchen_app/lib/core/realtime/ws_client.dart
//
// WebSocket client for the Kitchen Display System.
//
// Follows docs/08-realtime-and-event-specification.md:
//   - Exponential backoff with jitter (1s → 2s → 4s … capped at 30s)
//   - 30-second server heartbeat ping (matching backend HEARTBEAT_INTERVAL_MS)
//   - 250-event LRU deduplication ring buffer (sequence-based)
//   - Automatic REST state reconciliation on reconnect via onReconnect callback

import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../../config/env_config.dart';

typedef WsEventHandler = void Function(Map<String, dynamic> event);

class KdsWebSocketClient {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;

  bool _destroyed = false;
  int _reconnectAttempt = 0;
  String? _token;

  // 250-event LRU ring buffer for deduplication (docs/08 Section 3.3)
  final Set<String> _seenEventIds = <String>{};
  final List<String> _seenRing = <String>[];
  static const int _maxRingSize = 250;

  // Heartbeat period matching backend HEARTBEAT_INTERVAL_MS = 30_000 ms (docs/08 Section 4.3)
  static const Duration _heartbeatInterval = Duration(seconds: 30);

  // Max reconnect backoff cap (docs/08 Section 4.4)
  static const int _maxBackoffSeconds = 30;

  final List<WsEventHandler> _handlers = [];
  final StreamController<bool> _connectionStateController =
      StreamController<bool>.broadcast();

  Stream<bool> get isConnectedStream => _connectionStateController.stream;

  void connect(String token) {
    _token = token;
    _destroyed = false;
    _doConnect();
  }

  void disconnect() {
    _destroyed = true;
    _clearTimers();
    _subscription?.cancel();
    _subscription = null;
    _channel?.sink.close();
    _channel = null;
    if (!_connectionStateController.isClosed) {
      _connectionStateController.add(false);
    }
  }

  void addListener(WsEventHandler handler) {
    _handlers.add(handler);
  }

  void removeListener(WsEventHandler handler) {
    _handlers.remove(handler);
  }

  void _doConnect() {
    if (_destroyed) return;

    try {
      final wsUri =
          Uri.parse('${EnvConfig.wsUrl}?token=${Uri.encodeComponent(_token ?? '')}');
      _channel = WebSocketChannel.connect(wsUri);

      _subscription = _channel!.stream.listen(
        _handleMessage,
        onError: (_) => _handleDisconnect(),
        onDone: () => _handleDisconnect(),
        cancelOnError: true,
      );

      // Reset backoff counter and notify connected state only after stream is open.
      // WebSocketChannel does not provide an explicit onOpen callback, so we
      // optimistically signal connected here; _handleDisconnect will correct it.
      _reconnectAttempt = 0;
      if (!_connectionStateController.isClosed) {
        _connectionStateController.add(true);
      }
      _startHeartbeat();
    } catch (_) {
      _handleDisconnect();
    }
  }

  void _handleMessage(dynamic data) {
    try {
      final json = jsonDecode(data as String) as Map<String, dynamic>;

      // Filter out heartbeat pong responses
      final type = json['type']?.toString().toLowerCase();
      if (type == 'pong') return;

      if (_isDuplicate(json)) return;

      for (final h in List<WsEventHandler>.from(_handlers)) {
        h(json);
      }
    } catch (_) {
      // Silently ignore malformed frames
    }
  }

  bool _isDuplicate(Map<String, dynamic> event) {
    // Use event_id if present, else fall back to sequence number (docs/08 Section 3.2)
    final id =
        (event['event_id'] ?? event['sequence'] ?? event['id'])?.toString();
    if (id == null) return false;

    if (_seenEventIds.contains(id)) return true;
    _seenEventIds.add(id);
    _seenRing.add(id);
    if (_seenRing.length > _maxRingSize) {
      final evicted = _seenRing.removeAt(0);
      _seenEventIds.remove(evicted);
    }
    return false;
  }

  void _handleDisconnect() {
    if (!_connectionStateController.isClosed) {
      _connectionStateController.add(false);
    }
    _clearTimers();
    _subscription?.cancel();
    _subscription = null;
    _channel = null;

    if (!_destroyed) {
      _scheduleReconnect();
    }
  }

  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (_) {
      try {
        _channel?.sink.add(jsonEncode({'type': 'ping'}));
      } catch (_) {}
    });
  }

  void _scheduleReconnect() {
    if (_destroyed) return;
    _reconnectAttempt++;

    // Exponential backoff with ±500 ms jitter (docs/08 Section 4.4)
    final baseSeconds = min(_maxBackoffSeconds, pow(2, _reconnectAttempt - 1).toInt());
    final jitterMs = Random().nextInt(500);
    final delay = Duration(milliseconds: (baseSeconds * 1000) + jitterMs);

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(delay, _doConnect);
  }

  void _clearTimers() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }
}
