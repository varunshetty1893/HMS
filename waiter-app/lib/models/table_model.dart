class TableModel {
  final String id;
  final int tableNumber;
  final String? displayName;
  final String? locationDescription;
  final int capacity;
  final String status; // 'AVAILABLE' | 'OCCUPIED' | 'RESERVED'
  final bool isActive;
  final int displayOrder;
  final String? activeSessionId;
  final int? activeOrdersCount;
  final int? readyOrdersCount;
  final String? billStatus; // 'ISSUED' when billed but payment pending

  const TableModel({
    required this.id,
    required this.tableNumber,
    this.displayName,
    this.locationDescription,
    required this.capacity,
    required this.status,
    required this.isActive,
    required this.displayOrder,
    this.activeSessionId,
    this.activeOrdersCount,
    this.readyOrdersCount,
    this.billStatus,
  });

  factory TableModel.fromJson(Map<String, dynamic> json) {
    // Support both old (currentOccupancy/operationalStatus) and new (status) field layouts
    final statusRaw = json['status']?.toString() ??
        json['current_occupancy']?.toString() ??
        'AVAILABLE';

    return TableModel(
      id: json['id']?.toString() ?? '',
      tableNumber: json['table_number'] is int
          ? json['table_number'] as int
          : int.tryParse(json['table_number']?.toString() ?? '0') ?? 0,
      displayName: json['display_name']?.toString(),
      locationDescription: json['location_description']?.toString() ??
          json['floor_or_zone']?.toString(),
      capacity: json['capacity'] as int? ??
          json['seating_capacity'] as int? ?? 2,
      status: statusRaw,
      isActive: json['is_active'] == true,
      displayOrder: json['display_order'] as int? ?? 0,
      activeSessionId: json['active_session_id']?.toString() ??
          json['current_session_id']?.toString(),
      activeOrdersCount: json['active_orders_count'] as int?,
      readyOrdersCount: json['ready_orders_count'] as int?,
      billStatus: json['bill_status']?.toString(),
    );
  }

  bool get isAvailable => status == 'AVAILABLE';
  bool get isOccupied => status == 'OCCUPIED';
  bool get isBilled => isOccupied && billStatus == 'ISSUED';

  TableModel copyWith({
    String? status,
    String? activeSessionId,
    int? activeOrdersCount,
    int? readyOrdersCount,
    String? billStatus,
  }) {
    return TableModel(
      id: id,
      tableNumber: tableNumber,
      displayName: displayName,
      locationDescription: locationDescription,
      capacity: capacity,
      status: status ?? this.status,
      isActive: isActive,
      displayOrder: displayOrder,
      activeSessionId: activeSessionId ?? this.activeSessionId,
      activeOrdersCount: activeOrdersCount ?? this.activeOrdersCount,
      readyOrdersCount: readyOrdersCount ?? this.readyOrdersCount,
      billStatus: billStatus ?? this.billStatus,
    );
  }
}
