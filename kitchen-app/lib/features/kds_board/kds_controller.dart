import 'dart:async';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../core/network/api_exceptions.dart';
import '../../core/realtime/ws_client.dart';
import '../../core/storage/secure_token_storage.dart';
import '../../models/kitchen_order_model.dart';
import '../auth/auth_controller.dart';

class KdsBoardState {
  final List<KitchenOrderModel> orders;
  final bool isLoading;
  final bool isConnected;
  final String? errorMessage;
  final int placedCount;
  final int acceptedCount;
  final int preparingCount;
  final int readyCount;

  const KdsBoardState({
    this.orders = const [],
    this.isLoading = false,
    this.isConnected = true,
    this.errorMessage,
    this.placedCount = 0,
    this.acceptedCount = 0,
    this.preparingCount = 0,
    this.readyCount = 0,
  });

  KdsBoardState copyWith({
    List<KitchenOrderModel>? orders,
    bool? isLoading,
    bool? isConnected,
    String? errorMessage,
    int? placedCount,
    int? acceptedCount,
    int? preparingCount,
    int? readyCount,
  }) {
    return KdsBoardState(
      orders: orders ?? this.orders,
      isLoading: isLoading ?? this.isLoading,
      isConnected: isConnected ?? this.isConnected,
      errorMessage: errorMessage,
      placedCount: placedCount ?? this.placedCount,
      acceptedCount: acceptedCount ?? this.acceptedCount,
      preparingCount: preparingCount ?? this.preparingCount,
      readyCount: readyCount ?? this.readyCount,
    );
  }
}

final wsClientProvider = Provider<KdsWebSocketClient>((ref) => KdsWebSocketClient());

final kdsControllerProvider = StateNotifierProvider<KdsController, KdsBoardState>((ref) {
  return KdsController(
    apiClient: ref.read(apiClientProvider),
    wsClient: ref.read(wsClientProvider),
    tokenStorage: ref.read(tokenStorageProvider),
  );
});

class KdsController extends StateNotifier<KdsBoardState> {
  final ApiClient _apiClient;
  final KdsWebSocketClient _wsClient;
  final SecureTokenStorage _tokenStorage;
  final AudioPlayer _audioPlayer = AudioPlayer();

  StreamSubscription? _connSub;
  Timer? _elapsedTicker;

  KdsController({
    required ApiClient apiClient,
    required KdsWebSocketClient wsClient,
    required SecureTokenStorage tokenStorage,
  })  : _apiClient = apiClient,
        _wsClient = wsClient,
        _tokenStorage = tokenStorage,
        super(const KdsBoardState()) {
    _initRealtime();
    loadQueue();
    // Re-render elapsed timers every 10 seconds
    _elapsedTicker = Timer.periodic(const Duration(seconds: 10), (_) {
      if (mounted) {
        state = state.copyWith(); // triggers UI rebuild for updated elapsed display
      }
    });
  }

  @override
  void dispose() {
    _connSub?.cancel();
    _elapsedTicker?.cancel();
    _wsClient.disconnect();
    _audioPlayer.dispose();
    super.dispose();
  }

  void _initRealtime() async {
    final token = await _tokenStorage.getAccessToken();
    if (token != null) {
      _wsClient.connect(token);
    }

    _connSub = _wsClient.isConnectedStream.listen((connected) {
      state = state.copyWith(isConnected: connected);
      if (connected) {
        // Automatic HTTP reconciliation on reconnect (matching docs/08)
        loadQueue(quiet: true);
      }
    });

    _wsClient.addListener((event) {
      final eventType = event['event']?.toString() ?? '';
      if (eventType.startsWith('order.')) {
        if (eventType == 'order.created' || eventType == 'order.modified') {
          _playChime();
        }
        loadQueue(quiet: true);
      }
    });
  }

  void _playChime() {
    try {
      _audioPlayer.play(AssetSource('sounds/bell.mp3'));
    } catch (_) {}
  }

  Future<void> loadQueue({bool quiet = false}) async {
    if (!quiet) state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      final data = await _apiClient.getActiveQueue();
      final countsJson = data['counts'] as Map<String, dynamic>? ?? {};
      final ordersJson = (data['orders'] as List<dynamic>? ?? []);

      final orders = ordersJson
          .map((e) => KitchenOrderModel.fromJson(e as Map<String, dynamic>))
          .toList();

      state = state.copyWith(
        orders: orders,
        isLoading: false,
        placedCount: countsJson['placed'] as int? ?? 0,
        acceptedCount: countsJson['accepted'] as int? ?? 0,
        preparingCount: countsJson['preparing'] as int? ?? 0,
        readyCount: countsJson['ready'] as int? ?? 0,
      );
    } catch (e) {
      if (!quiet) {
        state = state.copyWith(
          isLoading: false,
          errorMessage: e.toString().replaceFirst('ApiException: ', ''),
        );
      }
    }
  }

  Future<void> acceptOrder(KitchenOrderModel order) async {
    try {
      await _apiClient.acceptOrder(order.id, order.version);
      await loadQueue(quiet: true);
    } on VersionConflictException {
      await loadQueue(quiet: true);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
    }
  }

  Future<void> rejectOrder(KitchenOrderModel order, String reason) async {
    try {
      await _apiClient.rejectOrder(order.id, order.version, reason);
      await loadQueue(quiet: true);
    } on VersionConflictException {
      await loadQueue(quiet: true);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
    }
  }

  Future<void> startPreparingOrder(KitchenOrderModel order) async {
    try {
      await _apiClient.startPreparingOrder(order.id, order.version);
      await loadQueue(quiet: true);
    } on VersionConflictException {
      await loadQueue(quiet: true);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
    }
  }

  Future<void> markOrderReady(KitchenOrderModel order) async {
    try {
      await _apiClient.markOrderReady(order.id, order.version);
      await loadQueue(quiet: true);
    } on VersionConflictException {
      await loadQueue(quiet: true);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
    }
  }

  Future<void> acknowledgeModifications(KitchenOrderModel order) async {
    try {
      await _apiClient.acknowledgeModifications(order.id);
      await loadQueue(quiet: true);
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
    }
  }
}
