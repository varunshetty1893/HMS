import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../core/realtime/ws_client.dart';
import '../../models/table_model.dart';
import '../auth/auth_controller.dart';
import '../../core/network/api_exceptions.dart';

final floorGridControllerProvider =
    StateNotifierProvider<FloorGridController, FloorGridState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final wsClient = ref.watch(wsClientProvider);
  return FloorGridController(apiClient, wsClient);
});

class FloorGridState {
  final bool isLoading;
  final String? error;
  final List<TableModel> tables;
  final String
      selectedFilter; // 'ALL', 'AVAILABLE', 'OCCUPIED', 'RESERVED', 'READY'
  final String searchQuery;

  const FloorGridState({
    this.isLoading = false,
    this.error,
    this.tables = const [],
    this.selectedFilter = 'ALL',
    this.searchQuery = '',
  });

  FloorGridState copyWith({
    bool? isLoading,
    String? error,
    List<TableModel>? tables,
    String? selectedFilter,
    String? searchQuery,
  }) {
    return FloorGridState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      tables: tables ?? this.tables,
      selectedFilter: selectedFilter ?? this.selectedFilter,
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }

  List<TableModel> get filteredTables {
    return tables.where((table) {
      if (searchQuery.isNotEmpty) {
        final q = searchQuery.toLowerCase();
        final matchesNumber = table.tableNumber.toString().contains(q);
        final matchesName =
            table.displayName?.toLowerCase().contains(q) ?? false;
        final matchesLocation =
            table.locationDescription?.toLowerCase().contains(q) ?? false;
        if (!matchesNumber && !matchesName && !matchesLocation) {
          return false;
        }
      }

      if (selectedFilter == 'ALL') return true;
      if (selectedFilter == 'AVAILABLE') return table.isAvailable;
      if (selectedFilter == 'OCCUPIED') return table.isOccupied;
      if (selectedFilter == 'RESERVED') return table.status == 'RESERVED';
      if (selectedFilter == 'READY') return (table.readyOrdersCount ?? 0) > 0;
      return true;
    }).toList();
  }

  int get totalReadyOrders {
    return tables.fold(0, (sum, t) => sum + (t.readyOrdersCount ?? 0));
  }
}

class FloorGridController extends StateNotifier<FloorGridState> {
  final ApiClient _apiClient;
  final WsClient _wsClient;

  FloorGridController(this._apiClient, this._wsClient)
      : super(const FloorGridState()) {
    _initWsListener();
    loadTables();
  }

  void _initWsListener() {
    _wsClient.messages.listen((msg) {
      final type = (msg['event'] ?? msg['type'])?.toString();
      if (type == 'table.status_changed' ||
          type == 'table.session_opened' ||
          type == 'table.session_closed' ||
          type == 'order.created' ||
          type == 'order.ready' ||
          type == 'order.served') {
        // Silently refresh tables on floor updates
        loadTables(silent: true);
      }
    });
  }

  Future<void> loadTables({bool silent = false}) async {
    if (!silent) {
      state = state.copyWith(isLoading: true, error: null);
    }
    try {
      final res = await _apiClient.get('/api/v1/waiter/tables');
      final list = (res as List)
          .map((item) => TableModel.fromJson(item as Map<String, dynamic>))
          .toList();
      state = state.copyWith(tables: list, isLoading: false, error: null);
    } catch (e) {
      if (!silent) {
        state = state.copyWith(isLoading: false, error: describeError(e));
      }
    }
  }

  void setFilter(String filter) {
    state = state.copyWith(selectedFilter: filter);
  }

  void setSearchQuery(String query) {
    state = state.copyWith(searchQuery: query);
  }
}
