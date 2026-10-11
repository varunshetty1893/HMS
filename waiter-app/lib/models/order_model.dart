/// Simplified order item used by the waiter screens (maps backend's WaiterOrderResponse items).
class OrderItemModel {
  final String id;
  final String itemName;
  final String? variantName;
  final int quantity;
  final double unitPrice;
  final double subtotal;
  final String? specialInstructions;

  const OrderItemModel({
    required this.id,
    required this.itemName,
    this.variantName,
    required this.quantity,
    required this.unitPrice,
    required this.subtotal,
    this.specialInstructions,
  });

  factory OrderItemModel.fromJson(Map<String, dynamic> json) {
    // Support both waiter-style (item_name, active_quantity) and simple style
    final qty = json['quantity'] as int? ??
        json['active_quantity'] as int? ??
        json['original_quantity'] as int? ?? 1;
    final price = double.tryParse(json['unit_price']?.toString() ??
            json['unit_price_snapshot']?.toString() ?? '0') ?? 0.0;
    final sub = double.tryParse(json['subtotal']?.toString() ??
            json['line_subtotal']?.toString() ?? '0') ?? 0.0;

    return OrderItemModel(
      id: json['id']?.toString() ?? '',
      itemName: json['item_name']?.toString() ??
          json['item_name_snapshot']?.toString() ?? '',
      variantName: json['variant_name']?.toString() ??
          json['variant_name_snapshot']?.toString(),
      quantity: qty,
      unitPrice: price,
      subtotal: sub.isNaN || sub == 0 ? price * qty : sub,
      specialInstructions: json['special_instructions']?.toString() ??
          json['item_notes']?.toString(),
    );
  }
}

/// Unified order model used across all waiter screens.
class OrderModel {
  final String id;
  final String orderNumber;
  final String? tableId;
  final int? tableNumber;
  final String status;
  final String source;
  final double subtotal;
  final int version;
  final bool hasUnacknowledgedMods;
  final String createdAt;
  final String updatedAt;
  final String? servedAt;
  final List<OrderItemModel> items;

  const OrderModel({
    required this.id,
    required this.orderNumber,
    this.tableId,
    this.tableNumber,
    required this.status,
    required this.source,
    required this.subtotal,
    required this.version,
    required this.hasUnacknowledgedMods,
    required this.createdAt,
    required this.updatedAt,
    this.servedAt,
    required this.items,
  });

  factory OrderModel.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List<dynamic>? ?? [];
    final itemsList = rawItems
        .map((e) => OrderItemModel.fromJson(e as Map<String, dynamic>))
        .toList();

    final sub = double.tryParse(json['subtotal']?.toString() ??
            json['order_subtotal']?.toString() ?? '0') ?? 0.0;

    return OrderModel(
      id: json['id']?.toString() ?? '',
      orderNumber: json['order_number']?.toString() ?? '',
      tableId: json['table_id']?.toString(),
      tableNumber: json['table_number'] as int?,
      status: json['status']?.toString() ?? 'PLACED',
      source: json['source']?.toString() ?? 'WAITER',
      subtotal: sub,
      version: json['version'] as int? ?? 1,
      hasUnacknowledgedMods: json['has_unacknowledged_mods'] == true,
      createdAt: json['created_at']?.toString() ??
          json['placed_at']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
      servedAt: json['served_at']?.toString(),
      items: itemsList,
    );
  }

  bool get isPlaced => status == 'PLACED';
  bool get isAccepted => status == 'ACCEPTED';
  bool get isPreparing => status == 'PREPARING';
  bool get isReady => status == 'READY';
  bool get isServed => status == 'SERVED';
  bool get isCancelled => status == 'CANCELLED';

  bool get canModify => isPlaced || isAccepted || isPreparing;
  bool get canCancel => isPlaced || isAccepted;
  bool get canServe => isReady;
}
