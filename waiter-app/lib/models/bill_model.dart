/// Bill line item representation using frozen historical snapshot.
class BillItemModel {
  final String? id;
  final String? orderId;
  final String orderNumber;
  final String itemCode;
  final String itemName;
  final String? variantCode;
  final String variantName;
  final String unit;
  final int quantityBilled;
  final double unitPriceSnapshot;
  final double lineTotal;

  const BillItemModel({
    this.id,
    this.orderId,
    required this.orderNumber,
    required this.itemCode,
    required this.itemName,
    this.variantCode,
    required this.variantName,
    required this.unit,
    required this.quantityBilled,
    required this.unitPriceSnapshot,
    required this.lineTotal,
  });

  factory BillItemModel.fromJson(Map<String, dynamic> json) {
    return BillItemModel(
      id: json['id']?.toString(),
      orderId: json['order_id']?.toString(),
      orderNumber: json['order_number']?.toString() ?? '',
      itemCode: json['item_code']?.toString() ?? '',
      itemName: json['item_name']?.toString() ?? '',
      variantCode: json['variant_code']?.toString(),
      variantName: json['variant_name']?.toString() ?? '',
      unit: json['unit']?.toString() ?? 'PORTION',
      quantityBilled: json['quantity_billed'] as int? ?? 1,
      unitPriceSnapshot: double.tryParse(json['unit_price_snapshot']?.toString() ?? '0') ?? 0.0,
      lineTotal: double.tryParse(json['line_total']?.toString() ?? '0') ?? 0.0,
    );
  }
}

/// Consolidated Bill representation.
class BillModel {
  final String id;
  final String billNumber;
  final String tableSessionId;
  final String tableId;
  final int? tableNumber;
  final String? tableDisplayName;
  final String status;
  final double subtotalAmount;
  final double discountAmount;
  final String? discountReason;
  final double taxableAmount;
  final double cgstRateSnapshot;
  final double cgstAmount;
  final double sgstRateSnapshot;
  final double sgstAmount;
  final double serviceChargeAmount;
  final double roundingAdjustment;
  final double grandTotal;
  final String? generatedByName;
  final String generatedAt;
  final String? paidAt;
  final List<BillItemModel> lineItems;

  const BillModel({
    required this.id,
    required this.billNumber,
    required this.tableSessionId,
    required this.tableId,
    this.tableNumber,
    this.tableDisplayName,
    required this.status,
    required this.subtotalAmount,
    required this.discountAmount,
    this.discountReason,
    required this.taxableAmount,
    required this.cgstRateSnapshot,
    required this.cgstAmount,
    required this.sgstRateSnapshot,
    required this.sgstAmount,
    required this.serviceChargeAmount,
    required this.roundingAdjustment,
    required this.grandTotal,
    this.generatedByName,
    required this.generatedAt,
    this.paidAt,
    required this.lineItems,
  });

  bool get isPaid => status == 'PAID';

  factory BillModel.fromJson(Map<String, dynamic> json) {
    final itemsList = (json['line_items'] as List<dynamic>? ?? [])
        .map((i) => BillItemModel.fromJson(i as Map<String, dynamic>))
        .toList();

    return BillModel(
      id: json['id']?.toString() ?? '',
      billNumber: json['bill_number']?.toString() ?? '',
      tableSessionId: json['table_session_id']?.toString() ?? '',
      tableId: json['table_id']?.toString() ?? '',
      tableNumber: json['table_number'] as int?,
      tableDisplayName: json['table_display_name']?.toString(),
      status: json['status']?.toString() ?? 'ISSUED',
      subtotalAmount: double.tryParse(json['subtotal_amount']?.toString() ?? '0') ?? 0.0,
      discountAmount: double.tryParse(json['discount_amount']?.toString() ?? '0') ?? 0.0,
      discountReason: json['discount_reason']?.toString(),
      taxableAmount: double.tryParse(json['taxable_amount']?.toString() ?? '0') ?? 0.0,
      cgstRateSnapshot: double.tryParse(json['cgst_rate_snapshot']?.toString() ?? '2.5') ?? 2.5,
      cgstAmount: double.tryParse(json['cgst_amount']?.toString() ?? '0') ?? 0.0,
      sgstRateSnapshot: double.tryParse(json['sgst_rate_snapshot']?.toString() ?? '2.5') ?? 2.5,
      sgstAmount: double.tryParse(json['sgst_amount']?.toString() ?? '0') ?? 0.0,
      serviceChargeAmount: double.tryParse(json['service_charge_amount']?.toString() ?? '0') ?? 0.0,
      roundingAdjustment: double.tryParse(json['rounding_adjustment']?.toString() ?? '0') ?? 0.0,
      grandTotal: double.tryParse(json['grand_total']?.toString() ?? '0') ?? 0.0,
      generatedByName: json['generated_by_name']?.toString(),
      generatedAt: json['generated_at']?.toString() ?? '',
      paidAt: json['paid_at']?.toString(),
      lineItems: itemsList,
    );
  }
}

/// Table bill preview or issued bill detail.
class TableBillModel {
  final int tableNumber;
  final String tableId;
  final String? tableDisplayName;
  final String tableSessionId;
  final String sessionCode;
  final bool hasUnacceptedPlacedOrders;
  final bool hasUnservedOrders;
  final String billStatus;
  final BillModel? bill;
  final List<BillItemModel> previewLineItems;
  final double? previewSubtotal;
  final double? previewTaxable;
  final double? previewCgst;
  final double? previewSgst;
  final double? previewGrandTotal;

  const TableBillModel({
    required this.tableNumber,
    required this.tableId,
    this.tableDisplayName,
    required this.tableSessionId,
    required this.sessionCode,
    required this.hasUnacceptedPlacedOrders,
    required this.hasUnservedOrders,
    required this.billStatus,
    this.bill,
    required this.previewLineItems,
    this.previewSubtotal,
    this.previewTaxable,
    this.previewCgst,
    this.previewSgst,
    this.previewGrandTotal,
  });

  bool get isBillIssued => billStatus == 'ISSUED';
  bool get isBillPaid => billStatus == 'PAID';
  // The billing API only issues a bill once every active order is served.
  // Keep the client action aligned with that rule so waiters are not offered
  // an action that the server will reject.
  bool get canGenerateBill =>
      !hasUnacceptedPlacedOrders && !hasUnservedOrders && bill == null;

  factory TableBillModel.fromJson(Map<String, dynamic> json) {
    final previewItems = (json['preview_line_items'] as List<dynamic>? ?? [])
        .map((i) => BillItemModel.fromJson(i as Map<String, dynamic>))
        .toList();

    return TableBillModel(
      tableNumber: json['table_number'] as int? ?? 0,
      tableId: json['table_id']?.toString() ?? '',
      tableDisplayName: json['table_display_name']?.toString(),
      tableSessionId: json['table_session_id']?.toString() ?? '',
      sessionCode: json['session_code']?.toString() ?? '',
      hasUnacceptedPlacedOrders: json['has_unaccepted_placed_orders'] as bool? ?? false,
      hasUnservedOrders: json['has_unserved_orders'] as bool? ?? false,
      billStatus: json['bill_status']?.toString() ?? 'NOT_GENERATED',
      bill: json['bill'] != null ? BillModel.fromJson(json['bill'] as Map<String, dynamic>) : null,
      previewLineItems: previewItems,
      previewSubtotal: double.tryParse(json['preview_subtotal']?.toString() ?? ''),
      previewTaxable: double.tryParse(json['preview_taxable']?.toString() ?? ''),
      previewCgst: double.tryParse(json['preview_cgst']?.toString() ?? ''),
      previewSgst: double.tryParse(json['preview_sgst']?.toString() ?? ''),
      previewGrandTotal: double.tryParse(json['preview_grand_total']?.toString() ?? ''),
    );
  }
}

/// Payment settlement representation.
class PaymentModel {
  final String id;
  final String billId;
  final String billNumber;
  final int? tableNumber;
  final String paymentMethod;
  /// Amount applied to the bill; this is the amount counted as revenue.
  final double amountPaid;
  /// Physical cash received, present only for CASH payments.
  final double? amountTendered;
  final double changeReturned;
  final String status;
  final String? referenceNumber;
  final String? notes;
  final String? recordedByName;
  final String? completedAt;

  const PaymentModel({
    required this.id,
    required this.billId,
    required this.billNumber,
    this.tableNumber,
    required this.paymentMethod,
    required this.amountPaid,
    this.amountTendered,
    required this.changeReturned,
    required this.status,
    this.referenceNumber,
    this.notes,
    this.recordedByName,
    this.completedAt,
  });

  factory PaymentModel.fromJson(Map<String, dynamic> json) {
    return PaymentModel(
      id: json['id']?.toString() ?? '',
      billId: json['bill_id']?.toString() ?? '',
      billNumber: json['bill_number']?.toString() ?? '',
      tableNumber: json['table_number'] as int?,
      paymentMethod: json['payment_method']?.toString() ?? 'CASH',
      amountPaid: double.tryParse(json['amount_paid']?.toString() ?? '0') ?? 0.0,
      amountTendered: json['amount_tendered'] == null
          ? null
          : double.tryParse(json['amount_tendered'].toString()),
      changeReturned:
          double.tryParse(json['change_returned']?.toString() ?? '0') ?? 0.0,
      status: json['status']?.toString() ?? 'COMPLETED',
      referenceNumber: json['reference_number']?.toString(),
      notes: json['notes']?.toString(),
      recordedByName: json['recorded_by_name']?.toString(),
      completedAt: json['completed_at']?.toString(),
    );
  }
}
