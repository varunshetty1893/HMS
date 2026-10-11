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

  const BillingState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.tableBill,
    this.bill,
    this.lastPayment,
    this.error,
  });

  BillingState copyWith({
    bool? isLoading,
    bool? isSubmitting,
    TableBillModel? tableBill,
    BillModel? bill,
    PaymentModel? lastPayment,
    String? error,
    bool clearError = false,
  }) {
    return BillingState(
      isLoading: isLoading ?? this.isLoading,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      tableBill: tableBill ?? this.tableBill,
      bill: bill ?? this.bill,
      lastPayment: lastPayment ?? this.lastPayment,
      error: clearError ? null : (error ?? this.error),
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

  Future<void> loadTableBill(int tableNumber) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final res = await _apiClient.get('/api/v1/waiter/tables/$tableNumber/bill');
      final tableBill = TableBillModel.fromJson(res);
      state = state.copyWith(
        isLoading: false,
        tableBill: tableBill,
        bill: tableBill.bill,
      );
    } on ApiException catch (e) {
      state = state.copyWith(isLoading: false, error: e.message);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'Failed to load table bill: $e');
    }
  }

  Future<BillModel?> generateBill({
    required int tableNumber,
    double discountAmount = 0.0,
    String? discountReason,
  }) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    final idempotencyKey = _generateIdempotencyKey();
    try {
      final payload = {
        'table_number': tableNumber,
        'discount_amount': discountAmount.toStringAsFixed(2),
        'discount_reason': discountReason,
      };

      final res = await _apiClient.post(
        '/api/v1/bills/generate',
        body: payload,
        headers: {'Idempotency-Key': idempotencyKey},
      );

      final bill = BillModel.fromJson(res);
      state = state.copyWith(isSubmitting: false, bill: bill);
      return bill;
    } on ApiException catch (e) {
      state = state.copyWith(isSubmitting: false, error: e.message);
      return null;
    } catch (e) {
      state = state.copyWith(isSubmitting: false, error: 'Failed to generate bill: $e');
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
