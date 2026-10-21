import 'dart:math';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../core/network/api_exceptions.dart';
import '../../models/bill_model.dart';
import '../auth/auth_controller.dart';

/// Per-item override: waiter can change unit price AND/OR quantity before billing.
class ItemOverride {
  final double unitPrice;
  final int quantity;
  final String reason;

  const ItemOverride({
    required this.unitPrice,
    required this.quantity,
    required this.reason,
  });

  ItemOverride copyWith({double? unitPrice, int? quantity, String? reason}) {
    return ItemOverride(
      unitPrice: unitPrice ?? this.unitPrice,
      quantity: quantity ?? this.quantity,
      reason: reason ?? this.reason,
    );
  }
}

/// Ad-hoc custom item added at billing time (e.g. milk, water, packaging).
class CustomItem {
  final String name;
  final int quantity;
  final double unitPrice;

  const CustomItem({
    required this.name,
    required this.quantity,
    required this.unitPrice,
  });

  double get lineTotal => unitPrice * quantity;

  CustomItem copyWith({String? name, int? quantity, double? unitPrice}) {
    return CustomItem(
      name: name ?? this.name,
      quantity: quantity ?? this.quantity,
      unitPrice: unitPrice ?? this.unitPrice,
    );
  }
}

class BillingState {
  final bool isLoading;
  final bool isSubmitting;
  final TableBillModel? tableBill;
  final BillModel? bill;
  final PaymentModel? lastPayment;
  final String? error;

  /// keyed by order_item id (UUID string from backend)
  final Map<String, ItemOverride> itemOverrides;

  /// Ad-hoc items not linked to any menu item
  final List<CustomItem> customItems;

  final double discountAmount;
  final String? discountReason;

  const BillingState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.tableBill,
    this.bill,
    this.lastPayment,
    this.error,
    this.itemOverrides = const {},
    this.customItems = const [],
    this.discountAmount = 0.0,
    this.discountReason,
  });

  BillingState copyWith({
    bool? isLoading,
    bool? isSubmitting,
    TableBillModel? tableBill,
    BillModel? bill,
    PaymentModel? lastPayment,
    String? error,
    bool clearError = false,
    Map<String, ItemOverride>? itemOverrides,
    List<CustomItem>? customItems,
    double? discountAmount,
    String? discountReason,
    bool clearDiscount = false,
  }) {
    return BillingState(
      isLoading: isLoading ?? this.isLoading,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      tableBill: tableBill ?? this.tableBill,
      bill: bill ?? this.bill,
      lastPayment: lastPayment ?? this.lastPayment,
      error: clearError ? null : (error ?? this.error),
      itemOverrides: itemOverrides ?? this.itemOverrides,
      customItems: customItems ?? this.customItems,
      discountAmount:
          clearDiscount ? 0.0 : (discountAmount ?? this.discountAmount),
      discountReason:
          clearDiscount ? null : (discountReason ?? this.discountReason),
    );
  }
}

class BillingController extends StateNotifier<BillingState> {
  final ApiClient _apiClient;

  BillingController({required ApiClient apiClient})
      : _apiClient = apiClient,
        super(const BillingState());

  String _generateIdempotencyKey() {
    final random = Random();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }

  // ── Item Overrides ──────────────────────────────────────────────────────────

  void setItemOverride(String itemId, ItemOverride ov) {
    final updated = Map<String, ItemOverride>.from(state.itemOverrides);
    updated[itemId] = ov;
    state = state.copyWith(itemOverrides: updated, clearError: true);
  }

  void removeItemOverride(String itemId) {
    final updated = Map<String, ItemOverride>.from(state.itemOverrides);
    updated.remove(itemId);
    state = state.copyWith(itemOverrides: updated, clearError: true);
  }

  void clearAllOverrides() {
    state = state.copyWith(itemOverrides: {}, clearError: true);
  }

  // ── Custom Items ────────────────────────────────────────────────────────────

  void addCustomItem(CustomItem item) {
    final updated = List<CustomItem>.from(state.customItems)..add(item);
    state = state.copyWith(customItems: updated, clearError: true);
  }

  void updateCustomItem(int index, CustomItem item) {
    final updated = List<CustomItem>.from(state.customItems)..[index] = item;
    state = state.copyWith(customItems: updated, clearError: true);
  }

  void removeCustomItem(int index) {
    final updated = List<CustomItem>.from(state.customItems)..removeAt(index);
    state = state.copyWith(customItems: updated, clearError: true);
  }

  void clearCustomItems() {
    state = state.copyWith(customItems: [], clearError: true);
  }

  // ── Discount ────────────────────────────────────────────────────────────────

  void setDiscount(double amount, String? reason) {
    state = state.copyWith(
        discountAmount: amount, discountReason: reason, clearError: true);
  }

  void removeDiscount() {
    state = state.copyWith(clearDiscount: true, clearError: true);
  }

  // ── Network ─────────────────────────────────────────────────────────────────

  Future<void> loadTableBill(int tableNumber) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final res =
          await _apiClient.get('/api/v1/waiter/tables/$tableNumber/bill');
      final tableBill = TableBillModel.fromJson(res);
      state = state.copyWith(
        isLoading: false,
        tableBill: tableBill,
        bill: tableBill.bill,
        discountAmount: tableBill.bill?.discountAmount ?? state.discountAmount,
        discountReason:
            tableBill.bill?.discountReason ?? state.discountReason,
      );
    } on ApiException catch (e) {
      state = state.copyWith(isLoading: false, error: e.message);
    } catch (e) {
      state = state.copyWith(
          isLoading: false, error: 'Failed to load table bill: $e');
    }
  }

  Future<BillModel?> generateBill({required int tableNumber}) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    final idempotencyKey = _generateIdempotencyKey();
    try {
      final overrides = state.itemOverrides.entries.map((e) {
        final ov = e.value;
        return {
          'order_item_id': e.key,
          'unit_price': ov.unitPrice.toStringAsFixed(2),
          'quantity_billed': ov.quantity,
          'reason': ov.reason,
        };
      }).toList();

      final customLines = state.customItems.map((c) => {
        'item_name': c.name,
        'quantity': c.quantity,
        'unit_price': c.unitPrice.toStringAsFixed(2),
        'reason': 'Custom item added at billing',
      }).toList();

      final payload = {
        'table_number': tableNumber,
        'discount_amount': state.discountAmount.toStringAsFixed(2),
        if (state.discountReason != null &&
            state.discountReason!.trim().isNotEmpty)
          'discount_reason': state.discountReason
        else if (state.discountAmount > 0)
          'discount_reason': 'Discount applied at billing',
        'price_overrides': overrides,
        'custom_line_items': customLines,
      };

      final res = await _apiClient.post(
        '/api/v1/bills/generate',
        body: payload,
        headers: {'Idempotency-Key': idempotencyKey},
      );

      final bill = BillModel.fromJson(res);
      state = state.copyWith(
        isSubmitting: false,
        bill: bill,
        discountAmount: bill.discountAmount,
        discountReason: bill.discountReason,
      );
      return bill;
    } on ApiException catch (e) {
      state = state.copyWith(isSubmitting: false, error: e.message);
      return null;
    } catch (e) {
      state = state.copyWith(
          isSubmitting: false, error: 'Failed to generate bill: $e');
      return null;
    }
  }

  Future<BillModel?> applyDiscountToIssuedBill({
    required String billId,
    required double discountAmount,
    required String reason,
  }) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      final payload = {
        'discount_amount': discountAmount.toStringAsFixed(2),
        'discount_reason': reason,
      };

      final res = await _apiClient.post(
        '/api/v1/bills/$billId/discount',
        body: payload,
      );

      final bill = BillModel.fromJson(res);
      state = state.copyWith(
        isSubmitting: false,
        bill: bill,
        discountAmount: bill.discountAmount,
        discountReason: bill.discountReason,
      );
      return bill;
    } on ApiException catch (e) {
      state = state.copyWith(isSubmitting: false, error: e.message);
      return null;
    } catch (e) {
      state = state.copyWith(
          isSubmitting: false, error: 'Failed to apply discount: $e');
      return null;
    }
  }

  Future<PaymentModel?> recordPayment({
    required String billId,
    required String paymentMethod,
    required double amountPaid,
    double? amountTendered,
    String? referenceNumber,
    String? notes,
  }) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    final idempotencyKey = _generateIdempotencyKey();
    try {
      final payload = {
        'payment_method': paymentMethod,
        'amount_paid': amountPaid.toStringAsFixed(2),
        'amount_tendered': amountTendered?.toStringAsFixed(2),
        'reference_number': referenceNumber,
        'notes': notes,
      };

      final res = await _apiClient.post(
        '/api/v1/bills/$billId/payments',
        body: payload,
        headers: {'Idempotency-Key': idempotencyKey},
      );

      final paymentData = res['payment'] as Map<String, dynamic>? ?? res;
      final payment = PaymentModel.fromJson(paymentData);
      state = state.copyWith(isSubmitting: false, lastPayment: payment);
      return payment;
    } on ApiException catch (e) {
      state = state.copyWith(isSubmitting: false, error: e.message);
      return null;
    } catch (e) {
      state = state.copyWith(
          isSubmitting: false, error: 'Failed to record payment: $e');
      return null;
    }
  }
}

final billingControllerProvider =
    StateNotifierProvider.autoDispose<BillingController, BillingState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return BillingController(apiClient: apiClient);
});
