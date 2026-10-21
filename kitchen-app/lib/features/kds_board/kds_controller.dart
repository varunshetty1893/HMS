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
  final List<KitchenCancellationAlert> cancellations;
  final Set<String> processingOrderIds;

  const KdsBoardState({
    this.orders = const [],
    this.isLoading = false,
    this.isConnected = false,
    this.errorMessage,
    this.placedCount = 0,
    this.acceptedCount = 0,
    this.preparingCount = 0,
    this.readyCount = 0,
    this.cancellations = const [],
    this.processingOrderIds = const {},
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
    List<KitchenCancellationAlert>? cancellations,
    Set<String>? processingOrderIds,
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
      cancellations: cancellations ?? this.cancellations,
      processingOrderIds: processingOrderIds ?? this.processingOrderIds,
    );
  }
}

final wsClientProvider = Provider<KdsWebSocketClient>((ref) {
  final client = KdsWebSocketClient();
  ref.onDispose(client.disconnect);
  return client;
});

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
  late final WsEventHandler _wsListener;
  // Cancellation alerts the cook already acknowledged on this device
  final Set<String> _dismissedCancellations = {};
  final Set<String> _seenCancellations = {};
  bool _firstQueueLoaded = false;
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
    _wsClient.removeListener(_wsListener);
    _wsClient.disconnect();
    _audioPlayer.dispose();
    super.dispose();
  }

  void _initRealtime() async {
    _connSub = _wsClient.isConnectedStream.listen((connected) {
      if (!mounted) return;
      state = state.copyWith(isConnected: connected);
      if (connected) loadQueue(quiet: true);
    });
    _wsListener = (event) {
      if (!mounted) return;
      final eventType = event['event']?.toString() ?? '';
      if (!eventType.startsWith('order.')) return;
      if (eventType == 'order.created' ||
          eventType == 'order.modified' ||
          eventType == 'order.cancelled') {
        _playChime();
      }
      loadQueue(quiet: true);
    };
    _wsClient.addListener(_wsListener);

    final token = await _tokenStorage.getAccessToken();
    if (!mounted) return;
    if (token != null && token.isNotEmpty) {
      _wsClient.connect(token);
    } else {
      state = state.copyWith(isConnected: false);
    }
  }

  void _playChime() {
    try {
      _audioPlayer.play(AssetSource('sounds/bell.mp3'));
    } catch (_) {}
  }

  Future<void> loadQueue({bool quiet = false}) async {
    if (!mounted) return;
    if (!quiet) state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      final data = await _apiClient.getActiveQueue();
      if (!mounted) return;
      final countsJson = data['counts'] as Map<String, dynamic>? ?? {};
      final ordersJson = (data['orders'] as List<dynamic>? ?? []);

      final orders = ordersJson
          .map((e) => KitchenOrderModel.fromJson(e as Map<String, dynamic>))
          .toList();

      final cancelJson = (data['recent_cancellations'] as List<dynamic>? ?? []);
      final allCancels = cancelJson
          .map((e) => KitchenCancellationAlert.fromJson(e as Map<String, dynamic>))
          .toList();
      // Beep once for each cancellation that appears AFTER the first load
      final isNewCancel = allCancels.any((c) => !_seenCancellations.contains(c.orderId));
      if (_firstQueueLoaded && isNewCancel) _playChime();
      _seenCancellations.addAll(allCancels.map((c) => c.orderId));
      _firstQueueLoaded = true;
      final cancels = allCancels
          .where((c) => !_dismissedCancellations.contains(c.orderId))
          .toList();

      state = state.copyWith(
        orders: orders,
        cancellations: cancels,
        isLoading: false,
        placedCount: countsJson['placed'] as int? ?? 0,
        acceptedCount: countsJson['accepted'] as int? ?? 0,
        preparingCount: countsJson['preparing'] as int? ?? 0,
        readyCount: countsJson['ready'] as int? ?? 0,
      );
    } catch (e) {
      if (!mounted) return;
      if (!quiet) {
        state = state.copyWith(
          isLoading: false,
          errorMessage: e.toString().replaceFirst('ApiException: ', ''),
        );
      }
    }
  }

  /// Cook acknowledged a cancellation banner ("Got it").
  void dismissCancellation(String orderId) {
    _dismissedCancellations.add(orderId);
    state = state.copyWith(
      cancellations:
          state.cancellations.where((c) => c.orderId != orderId).toList(),
    );
  }

  Future<void> acceptOrder(KitchenOrderModel order) async {
    if (!_beginAction(order.id)) return;
    try {
      await _apiClient.acceptOrder(order.id, order.version);
      await loadQueue(quiet: true);
    } on VersionConflictException {
      await loadQueue(quiet: true);
    } catch (e) {
      _showActionError(e);
    } finally {
      _finishAction(order.id);
    }
  }

  Future<void> rejectOrder(KitchenOrderModel order, String reason) async {
    if (!_beginAction(order.id)) return;
    try {
      await _apiClient.rejectOrder(order.id, order.version, reason);
      await loadQueue(quiet: true);
    } on VersionConflictException {
      await loadQueue(quiet: true);
    } catch (e) {
      _showActionError(e);
    } finally {
      _finishAction(order.id);
    }
  }

  Future<void> startPreparingOrder(KitchenOrderModel order) async {
    if (!_beginAction(order.id)) return;
    try {
      await _apiClient.startPreparingOrder(order.id, order.version);
      await loadQueue(quiet: true);
    } on VersionConflictException {
      await loadQueue(quiet: true);
    } catch (e) {
      _showActionError(e);
    } finally {
      _finishAction(order.id);
    }
  }

  Future<void> markOrderReady(KitchenOrderModel order) async {
    if (!_beginAction(order.id)) return;
    try {
      await _apiClient.markOrderReady(order.id, order.version);
      await loadQueue(quiet: true);
    } on VersionConflictException {
      await loadQueue(quiet: true);
    } catch (e) {
      _showActionError(e);
    } finally {
      _finishAction(order.id);
    }
  }

  Future<void> acknowledgeModifications(KitchenOrderModel order) async {
    if (!_beginAction(order.id)) return;
    try {
      await _apiClient.acknowledgeModifications(order.id);
      await loadQueue(quiet: true);
    } catch (e) {
      _showActionError(e);
    } finally {
      _finishAction(order.id);
    }
  }

  bool _beginAction(String orderId) {
    if (!mounted || state.processingOrderIds.contains(orderId)) return false;
    state = state.copyWith(
      processingOrderIds: {...state.processingOrderIds, orderId},
      errorMessage: null,
    );
    return true;
  }

  void _finishAction(String orderId) {
    if (!mounted) return;
    state = state.copyWith(
      processingOrderIds: {...state.processingOrderIds}..remove(orderId),
      errorMessage: state.errorMessage,
    );
  }

  void _showActionError(Object error) {
    if (!mounted) return;
    state = state.copyWith(errorMessage: describeError(error));
  }
}
