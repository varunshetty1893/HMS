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
    );
  }
}
