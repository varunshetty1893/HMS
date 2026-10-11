class KitchenItemModel {
  final String orderItemId;
  final String itemCode;
  final String itemName;
  final String variantName;
  final int originalQuantity;
  final int activeQuantity;
  final String itemStatus;
  final String? itemNotes;

  const KitchenItemModel({
    required this.orderItemId,
    required this.itemCode,
    required this.itemName,
    required this.variantName,
    required this.originalQuantity,
    required this.activeQuantity,
    required this.itemStatus,
    this.itemNotes,
  });

  factory KitchenItemModel.fromJson(Map<String, dynamic> json) {
    return KitchenItemModel(
      orderItemId: json['order_item_id'] as String,
      itemCode: json['item_code'] as String,
      itemName: json['item_name'] as String,
      variantName: json['variant_name'] as String,
      originalQuantity: json['original_quantity'] as int? ?? 1,
      activeQuantity: json['active_quantity'] as int? ?? 1,
      itemStatus: json['item_status'] as String? ?? 'ACTIVE',
      itemNotes: json['item_notes'] as String?,
    );
  }
}

class KitchenModificationEventModel {
  final String modificationEventId;
  final String modificationType;
  final String itemName;
  final int previousQuantity;
  final int newQuantity;
  final String reason;
  final String? modifiedByName;
  final DateTime createdAt;

  const KitchenModificationEventModel({
    required this.modificationEventId,
    required this.modificationType,
    required this.itemName,
    required this.previousQuantity,
    required this.newQuantity,
    required this.reason,
    this.modifiedByName,
    required this.createdAt,
  });

  factory KitchenModificationEventModel.fromJson(Map<String, dynamic> json) {
    return KitchenModificationEventModel(
      modificationEventId: json['modification_event_id'] as String,
      modificationType: json['modification_type'] as String,
      itemName: json['item_name'] as String? ?? 'Item',
      previousQuantity: json['previous_quantity'] as int? ?? 0,
      newQuantity: json['new_quantity'] as int? ?? 0,
      reason: json['reason'] as String? ?? '',
      modifiedByName: json['modified_by_name'] as String?,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
    );
  }
}
