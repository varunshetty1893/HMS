import 'kitchen_item_model.dart';

class KitchenOrderModel {
  final String id;
  final String orderNumber;
  final String tableId;
  final int tableNumber;
  final String tableDisplayName;
  final String source;
  final String? waiterName;
  final String status;
  final DateTime placedAt;
  final DateTime? acceptedAt;
  final DateTime? preparingAt;
  final DateTime? readyAt;
  final int elapsedSeconds;
  final int version;
  final String? specialInstructions;
  final bool hasUnacknowledgedMods;
  final List<KitchenItemModel> items;
  final List<KitchenModificationEventModel> unacknowledgedModifications;
  final String? rejectionReason;

  const KitchenOrderModel({
    required this.id,
    required this.orderNumber,
    required this.tableId,
    required this.tableNumber,
    required this.tableDisplayName,
    required this.source,
    this.waiterName,
    required this.status,
    required this.placedAt,
    this.acceptedAt,
    this.preparingAt,
    this.readyAt,
    this.elapsedSeconds = 0,
    required this.version,
    this.specialInstructions,
    this.hasUnacknowledgedMods = false,
    required this.items,
    this.unacknowledgedModifications = const [],
    this.rejectionReason,
  });

  factory KitchenOrderModel.fromJson(Map<String, dynamic> json) {
    return KitchenOrderModel(
      id: json['id'] as String,
      orderNumber: json['order_number'] as String,
      tableId: json['table_id'] as String,
      tableNumber: json['table_number'] as int? ?? 0,
      tableDisplayName: json['table_display_name'] as String? ?? 'Table',
      source: json['source'] as String? ?? 'CUSTOMER_QR',
      waiterName: json['waiter_name'] as String?,
      status: json['status'] as String,
      placedAt: DateTime.tryParse(json['placed_at']?.toString() ?? '') ?? DateTime.now(),
      acceptedAt: json['accepted_at'] != null ? DateTime.tryParse(json['accepted_at']) : null,
      preparingAt: json['preparing_at'] != null ? DateTime.tryParse(json['preparing_at']) : null,
      readyAt: json['ready_at'] != null ? DateTime.tryParse(json['ready_at']) : null,
      elapsedSeconds: json['elapsed_seconds'] as int? ?? 0,
      version: json['version'] as int? ?? 1,
      specialInstructions: json['special_instructions'] as String?,
      hasUnacknowledgedMods: json['has_unacknowledged_mods'] as bool? ?? false,
      items: (json['items'] as List<dynamic>? ?? [])
          .map((e) => KitchenItemModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      unacknowledgedModifications: (json['unacknowledged_modifications'] as List<dynamic>? ?? [])
          .map((e) => KitchenModificationEventModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      rejectionReason: json['rejection_reason'] as String? ?? json['rejectionReason'] as String?,
    );
  }

  KitchenOrderModel copyWith({
    String? status,
    int? version,
    DateTime? acceptedAt,
    DateTime? preparingAt,
    DateTime? readyAt,
    bool? hasUnacknowledgedMods,
    List<KitchenItemModel>? items,
    String? rejectionReason,
  }) {
    return KitchenOrderModel(
      id: id,
      orderNumber: orderNumber,
      tableId: tableId,
      tableNumber: tableNumber,
      tableDisplayName: tableDisplayName,
      source: source,
      waiterName: waiterName,
      status: status ?? this.status,
      placedAt: placedAt,
      acceptedAt: acceptedAt ?? this.acceptedAt,
      preparingAt: preparingAt ?? this.preparingAt,
      readyAt: readyAt ?? this.readyAt,
      elapsedSeconds: elapsedSeconds,
      version: version ?? this.version,
      specialInstructions: specialInstructions,
      hasUnacknowledgedMods: hasUnacknowledgedMods ?? this.hasUnacknowledgedMods,
      items: items ?? this.items,
      unacknowledgedModifications: unacknowledgedModifications,
      rejectionReason: rejectionReason ?? this.rejectionReason,
    );
  }
}

/// A recently cancelled order the kitchen must STOP cooking / DISCARD.
/// Comes from `recent_cancellations` of `GET /kitchen/orders/active` (no prices).
class KitchenCancellationAlert {
  final String orderId;
  final String orderNumber;
  final String tableName;
  final String? cancelledByRole;
  final String? reason;
  final bool forced;

  /// STOP_COOKING | DISCARD_READY_FOOD | REMOVE_TICKET
  final String action;
  final List<String> items;

  const KitchenCancellationAlert({
    required this.orderId,
    required this.orderNumber,
    required this.tableName,
    this.cancelledByRole,
    this.reason,
    this.forced = false,
    this.action = 'REMOVE_TICKET',
    this.items = const [],
  });

  factory KitchenCancellationAlert.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List<dynamic>? ?? const [];
    return KitchenCancellationAlert(
      orderId: json['order_id']?.toString() ?? '',
      orderNumber: json['order_number']?.toString() ?? '',
      tableName: json['table_display_name']?.toString() ?? '',
      cancelledByRole: json['cancelled_by_role']?.toString(),
      reason: json['reason']?.toString(),
      forced: json['forced'] == true,
      action: json['kitchen_action']?.toString() ?? 'REMOVE_TICKET',
      items: rawItems.map((e) {
        final m = e as Map<String, dynamic>;
        return '${m['quantity'] ?? 1}x ${m['item_name'] ?? ''} (${m['variant_name'] ?? ''})';
      }).toList(),
    );
  }

  String get headline {
    switch (action) {
      case 'STOP_COOKING':
        return 'STOP COOKING';
      case 'DISCARD_READY_FOOD':
        return 'DISCARD READY FOOD';
      default:
        return 'ORDER CANCELLED';
    }
  }
}
