import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../../config/env_config.dart';
import '../storage/secure_token_storage.dart';

typedef WsEventHandler = void Function(Map<String, dynamic> event);

class WaiterWebSocketClient {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;

  bool _destroyed = false;
  int _reconnectAttempt = 0;
  String? _token;

  final Set<String> _seenEventIds = <String>{};
  final List<String> _seenRing = <String>[];
  static const int _maxRingSize = 250;

  final List<WsEventHandler> _handlers = [];

  final StreamController<bool> _connectionStateController =
      StreamController<bool>.broadcast();

  /// Broadcast stream of parsed WS event maps. Controllers/providers listen to this.
  final StreamController<Map<String, dynamic>> _messagesController =
      StreamController<Map<String, dynamic>>.broadcast();

  Stream<bool> get isConnectedStream => _connectionStateController.stream;

  /// Stream of incoming WebSocket event payloads (deduplicated).
  Stream<Map<String, dynamic>> get messages => _messagesController.stream;

  void connect(String token) {
    _token = token;
    _destroyed = false;
    _doConnect();
  }

  void disconnect() {
    _destroyed = true;
    _clearTimers();
    _subscription?.cancel();
    _channel?.sink.close();
    _channel = null;
    _connectionStateController.add(false);
  }

  void addListener(WsEventHandler handler) {
    _handlers.add(handler);
  }

  void removeListener(WsEventHandler handler) {
    _handlers.remove(handler);
  }

  Future<void> _doConnect() async {
    if (_destroyed) return;

    // Always connect with the freshest access token (it may have been renewed
    // by the REST client since the socket was first opened).
    try {
      final fresh = await SecureTokenStorage().getAccessToken();
      if (fresh != null && fresh.isNotEmpty) _token = fresh;
    } catch (_) {}
    if (_destroyed) return;

    try {
      final wsUri = Uri.parse(
          '${EnvConfig.wsUrl}?token=${Uri.encodeComponent(_token ?? '')}');
      _channel = WebSocketChannel.connect(wsUri);
      _connectionStateController.add(true);
      _reconnectAttempt = 0;
      _startHeartbeat();

      _subscription = _channel!.stream.listen(
        (data) {
          _handleMessage(data);
        },
        onError: (err) {
          _onDisconnect();
        },
        onDone: () {
          _onDisconnect();
        },
        cancelOnError: true,
      );
    } catch (_) {
      _onDisconnect();
    }
  }

  void _handleMessage(dynamic data) {
    try {
      final Map<String, dynamic> parsed = jsonDecode(data.toString());

      // Filter heartbeat pong responses (docs/08 Section 4.3)
      final msgType = (parsed['type'] ?? '').toString().toLowerCase();
      if (msgType == 'pong') return;

      // Deduplication: prefer event_id, fall back to sequence, then composite key
      final eventId = parsed['event_id']?.toString() ??
          parsed['sequence']?.toString() ??
          '${parsed['event']}_${parsed['order_id'] ?? parsed['table_id']}_${parsed['timestamp']}';

      if (_seenEventIds.contains(eventId)) {
        return;
      }
      _recordEventId(eventId);

      // Broadcast to stream-based listeners
      _messagesController.add(parsed);

      // Also call legacy handler-based listeners
      for (final handler in List<WsEventHandler>.from(_handlers)) {
        handler(parsed);
      }
    } catch (_) {}
  }

  void _recordEventId(String eventId) {
    _seenEventIds.add(eventId);
    _seenRing.add(eventId);
    if (_seenRing.length > _maxRingSize) {
      final oldest = _seenRing.removeAt(0);
      _seenEventIds.remove(oldest);
    }
  }

  void _onDisconnect() {
    _clearTimers();
    _connectionStateController.add(false);
    _subscription?.cancel();
    _channel = null;

    if (_destroyed) return;

    final delaySeconds = min(pow(2, _reconnectAttempt).toInt(), 30);
    _reconnectAttempt++;
    _reconnectTimer = Timer(Duration(seconds: delaySeconds), () {
      _doConnect();
    });
  }

  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    // 30-second heartbeat matching backend HEARTBEAT_INTERVAL_MS (docs/08 Section 4.3)
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      try {
        _channel?.sink.add(jsonEncode({'type': 'ping'}));
      } catch (_) {}
    });
  }

  void _clearTimers() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }
}

/// Convenience alias used throughout controller files.
typedef WsClient = WaiterWebSocketClient;
