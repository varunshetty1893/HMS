import 'dart:async';
import 'dart:math';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../models/menu_search_result.dart';
import '../../models/table_model.dart';
import '../auth/auth_controller.dart';

// Cart item holds selected variant + quantity
class CartItem {
  final MenuItemResult item;
  final MenuVariantResult variant;
  int quantity;
  String? specialInstructions;

  CartItem({
    required this.item,
    required this.variant,
    this.quantity = 1,
    this.specialInstructions,
  });

  double get lineTotal => variant.price * quantity;

  String get cartKey => '${item.id}__${variant.id}';
}

class OrderEntryState {
  final bool isSearching;
  final String searchQuery;
  final List<MenuItemResult> searchResults;
  final String? searchError;
  final Map<String, CartItem> cart; // keyed by cartKey
  final bool isSubmitting;
  final String? submitError;

  const OrderEntryState({
    this.isSearching = false,
    this.searchQuery = '',
    this.searchResults = const [],
    this.searchError,
    this.cart = const {},
    this.isSubmitting = false,
    this.submitError,
  });

  OrderEntryState copyWith({
    bool? isSearching,
    String? searchQuery,
    List<MenuItemResult>? searchResults,
    String? searchError,
    Map<String, CartItem>? cart,
    bool? isSubmitting,
    String? submitError,
  }) {
    return OrderEntryState(
      isSearching: isSearching ?? this.isSearching,
      searchQuery: searchQuery ?? this.searchQuery,
      searchResults: searchResults ?? this.searchResults,
      searchError: searchError,
      cart: cart ?? this.cart,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      submitError: submitError,
    );
  }

  int get cartItemCount => cart.values.fold(0, (sum, ci) => sum + ci.quantity);

  double get cartTotal => cart.values.fold(0.0, (sum, ci) => sum + ci.lineTotal);

  List<CartItem> get cartItems => cart.values.toList();
}

final orderEntryControllerProvider =
    StateNotifierProvider.autoDispose<OrderEntryController, OrderEntryState>(
        (ref) {
  final apiClient = ref.watch(apiClientProvider);
  return OrderEntryController(apiClient);
});

class OrderEntryController extends StateNotifier<OrderEntryState> {
  final ApiClient _apiClient;

  OrderEntryController(this._apiClient) : super(const OrderEntryState());

  Timer? _debounce;
  int _searchSeq = 0;

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  /// Debounced entry point (call from TextField.onChanged).
  void search(String query) {
    final trimmed = query.trim();
    _debounce?.cancel();
    _searchSeq++; // purani in-flight responses ignore hongi

    if (trimmed.isEmpty) {
      state = state.copyWith(
          searchQuery: '', searchResults: [], isSearching: false, searchError: null);
      return;
    }

    state = state.copyWith(searchQuery: trimmed, isSearching: true, searchError: null);
    _debounce = Timer(const Duration(milliseconds: 300), () => _runSearch(trimmed));
  }

  Future<void> _runSearch(String trimmed) async {
    final seq = ++_searchSeq;
    try {
      dynamic res;
      final isShortCode = RegExp(r'^[A-Za-z]{2}-[A-Za-z]').hasMatch(trimmed);
      if (isShortCode) {
        res = await _apiClient.get(
            '/api/v1/waiter/menu/code-search?code=${Uri.encodeQueryComponent(trimmed.toUpperCase())}');
      } else {
        res = await _apiClient
            .get('/api/v1/waiter/menu/search?q=${Uri.encodeQueryComponent(trimmed)}');
      }

      if (seq != _searchSeq) return; // newer search aa chuki hai

      // Backend shape: { "query": "...", "results": [ {item_id, item_code, name, ...} ] }
      List<dynamic> raw = const [];
      if (res is List) {
        raw = res;
      } else if (res is Map && res['results'] is List) {
        raw = res['results'] as List;
      } else if (res is Map && res['items'] is List) {
        raw = res['items'] as List;
      }

      final items = raw
          .map((e) => MenuItemResult.fromJson(e as Map<String, dynamic>))
          .where((i) => i.id.isNotEmpty && i.name.isNotEmpty)
          .toList();

      state = state.copyWith(searchResults: items, isSearching: false, searchError: null);
    } catch (e) {
      if (seq != _searchSeq) return;
      state = state.copyWith(isSearching: false, searchError: e.toString());
    }
  }

  void addToCart(MenuItemResult item, MenuVariantResult variant) {
    final newCart = Map<String, CartItem>.from(state.cart);
    final key = '${item.id}__${variant.id}';
    if (newCart.containsKey(key)) {
      newCart[key]!.quantity++;
    } else {
      newCart[key] = CartItem(item: item, variant: variant);
    }
    state = state.copyWith(cart: newCart);
  }

  void updateCartQuantity(String cartKey, int newQty) {
    final newCart = Map<String, CartItem>.from(state.cart);
    if (newQty <= 0) {
      newCart.remove(cartKey);
    } else {
      newCart[cartKey]?.quantity = newQty;
    }
    state = state.copyWith(cart: newCart);
  }

  void setSpecialInstructions(String cartKey, String instructions) {
    final newCart = Map<String, CartItem>.from(state.cart);
    newCart[cartKey]?.specialInstructions =
        instructions.trim().isEmpty ? null : instructions.trim();
    state = state.copyWith(cart: newCart);
  }

  void clearCart() {
    state = state.copyWith(cart: {});
  }

  Future<bool> submitOrder({
    required TableModel table,
    String? specialRequestNotes,
  }) async {
    if (state.cart.isEmpty) return false;

    state = state.copyWith(isSubmitting: true, submitError: null);

    final idempotencyKey = _generateIdempotencyKey();
    // Backend (WaiterOrderCreate / OrderItemCreate) strict hai: sirf yehi fields allowed.
    final items = state.cart.values.map((ci) {
      return {
        'variant_id': ci.variant.id,
        'quantity': ci.quantity,
        if (ci.specialInstructions != null) 'item_notes': ci.specialInstructions,
      };
    }).toList();

    final data = {
      'table_id': table.id,
      'items': items,
      if (specialRequestNotes != null && specialRequestNotes.trim().isNotEmpty)
        'special_instructions': specialRequestNotes.trim(),
    };

    try {
      await _apiClient.post(
        '/api/v1/waiter/orders',
        data: data,
        headers: {'Idempotency-Key': idempotencyKey},
      );
      state = state.copyWith(isSubmitting: false, cart: {});
      return true;
    } catch (e) {
      state = state.copyWith(isSubmitting: false, submitError: e.toString());
      return false;
    }
  }

  String _generateIdempotencyKey() {
    final rng = Random.secure();
    final bytes = List<int>.generate(16, (_) => rng.nextInt(256));
    return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
}
