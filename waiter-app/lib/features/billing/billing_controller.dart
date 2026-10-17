import 'dart:math';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../core/network/api_exceptions.dart';
import '../../models/bill_model.dart';
import '../auth/auth_controller.dart';

class BillingState {
  final bool isLoading;
  final bool isSubmitting;
  final TableBillModel? tableBill;
  final BillModel? bill;
  final PaymentModel? lastPayment;
  final String? error;
  final double discountAmount;
  final String? discountReason;
  final Map<String, double> priceOverrides;
  final Map<String, String> priceOverrideReasons;

  const BillingState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.tableBill,
    this.bill,
    this.lastPayment,
    this.error,
    this.discountAmount = 0.0,
    this.discountReason,
    this.priceOverrides = const {},
    this.priceOverrideReasons = const {},
  });

  BillingState copyWith({
    bool? isLoading,
    bool? isSubmitting,
    TableBillModel? tableBill,
    BillModel? bill,
    PaymentModel? lastPayment,
    String? error,
    bool clearError = false,
    double? discountAmount,
    String? discountReason,
    bool clearDiscount = false,
    Map<String, double>? priceOverrides,
    Map<String, String>? priceOverrideReasons,
  }) {
    return BillingState(
      isLoading: isLoading ?? this.isLoading,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      tableBill: tableBill ?? this.tableBill,
      bill: bill ?? this.bill,
      lastPayment: lastPayment ?? this.lastPayment,
      error: clearError ? null : (error ?? this.error),
      discountAmount: clearDiscount ? 0.0 : (discountAmount ?? this.discountAmount),
      discountReason: clearDiscount ? null : (discountReason ?? this.discountReason),
      priceOverrides: priceOverrides ?? this.priceOverrides,
      priceOverrideReasons: priceOverrideReasons ?? this.priceOverrideReasons,
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

  void setDiscount(double amount, String? reason) {
    state = state.copyWith(
      discountAmount: amount,
      discountReason: reason,
      clearError: true,
    );
  }

  void removeDiscount() {
    state = state.copyWith(clearDiscount: true, clearError: true);
  }

  void setPriceOverride(String itemId, double newPrice, String reason) {
    final newOverrides = Map<String, double>.from(state.priceOverrides);
    final newReasons = Map<String, String>.from(state.priceOverrideReasons);
    newOverrides[itemId] = newPrice;
    newReasons[itemId] = reason;
    state = state.copyWith(
      priceOverrides: newOverrides,
      priceOverrideReasons: newReasons,
      clearError: true,
    );
  }

  void removePriceOverride(String itemId) {
    final newOverrides = Map<String, double>.from(state.priceOverrides);
    final newReasons = Map<String, String>.from(state.priceOverrideReasons);
    newOverrides.remove(itemId);
    newReasons.remove(itemId);
    state = state.copyWith(
      priceOverrides: newOverrides,
      priceOverrideReasons: newReasons,
      clearError: true,
    );
  }

  Future<void> loadTableBill(int tableNumber) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final res = await _apiClient.get('/api/v1/waiter/tables/$tableNumber/bill');
      final tableBill = TableBillModel.fromJson(res);
      state = state.copyWith(
        isLoading: false,
        tableBill: tableBill,
        bill: tableBill.bill,
        discountAmount: tableBill.bill?.discountAmount ?? state.discountAmount,
        discountReason: tableBill.bill?.discountReason ?? state.discountReason,
      );
    } on ApiException catch (e) {
      state = state.copyWith(isLoading: false, error: e.message);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'Failed to load table bill: $e');
    }
  }

  Future<BillModel?> generateBill({
    required int tableNumber,
  }) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    final idempotencyKey = _generateIdempotencyKey();
    try {
      final overrides = state.priceOverrides.entries.map((e) {
        return {
          'order_item_id': e.key,
          'unit_price': e.value.toStringAsFixed(2),
          'reason': state.priceOverrideReasons[e.key] ?? 'Price adjusted at billing',
        };
      }).toList();

      final payload = {
        'table_number': tableNumber,
        'discount_amount': state.discountAmount.toStringAsFixed(2),
        if (state.discountReason != null && state.discountReason!.isNotEmpty)
          'discount_reason': state.discountReason
        else if (state.discountAmount > 0)
          'discount_reason': 'Discount applied at billing',
        'price_overrides': overrides,
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
      state = state.copyWith(isSubmitting: false, error: 'Failed to generate bill: $e');
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
      state = state.copyWith(isSubmitting: false, error: 'Failed to apply discount: $e');
      return null;
    }
  }

  Future<PaymentModel?> recordPayment({
    required String billId,
    required String paymentMethod,
    required double amountPaid,
    String? referenceNumber,
    String? notes,
  }) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    final idempotencyKey = _generateIdempotencyKey();
    try {
      final payload = {
        'payment_method': paymentMethod,
        'amount_paid': amountPaid.toStringAsFixed(2),
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
      state = state.copyWith(isSubmitting: false, error: 'Failed to record payment: $e');
      return null;
    }
  }
}

final billingControllerProvider =
    StateNotifierProvider.autoDispose<BillingController, BillingState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return BillingController(apiClient: apiClient);
});
