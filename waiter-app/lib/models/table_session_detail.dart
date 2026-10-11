import 'table_model.dart';
import 'order_model.dart';

class TableSessionDetail {
  final TableModel table;
  final String? sessionId;
  final String? sessionStatus;
  final double currentExposure;
  final double unpaidSpendLimit;
  final List<OrderModel> activeOrders;

  const TableSessionDetail({
    required this.table,
    this.sessionId,
    this.sessionStatus,
    required this.currentExposure,
    required this.unpaidSpendLimit,
    required this.activeOrders,
  });

  factory TableSessionDetail.fromJson(Map<String, dynamic> json) {
    // Build TableModel from the nested or flat payload
    final tableJson = json['table'] as Map<String, dynamic>? ?? {
      'id': json['table_id'] ?? '',
      'table_number': json['table_number'] ?? 0,
      'display_name': json['table_display_name'],
      'capacity': json['capacity'] ?? 2,
      'status': json['table_status'] ?? 'AVAILABLE',
      'is_active': true,
      'display_order': 0,
    };
    final table = TableModel.fromJson(tableJson);

    final rawOrders = json['orders'] as List<dynamic>? ?? [];
    final ordersList = rawOrders
        .map((e) => OrderModel.fromJson(e as Map<String, dynamic>))
        .toList();

    final exposure = double.tryParse(
            json['current_exposure']?.toString() ??
            json['current_outstanding_amount']?.toString() ?? '0') ?? 0.0;
    final limit = double.tryParse(
            json['unpaid_spend_limit']?.toString() ??
            json['custom_outstanding_limit']?.toString() ?? '5000') ?? 5000.0;

    return TableSessionDetail(
      table: table,
      sessionId: json['session_id']?.toString(),
      sessionStatus: json['session_status']?.toString(),
      currentExposure: exposure,
      unpaidSpendLimit: limit,
      activeOrders: ordersList,
    );
  }

  double get remainingLimit =>
      (unpaidSpendLimit - currentExposure).clamp(0.0, unpaidSpendLimit);

  double get limitProgress =>
      (currentExposure / unpaidSpendLimit).clamp(0.0, 1.0);
}
