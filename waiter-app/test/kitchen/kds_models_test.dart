import 'package:flutter_test/flutter_test.dart';
import 'package:waiter_app/kitchen/models/kitchen_item_model.dart';
import 'package:waiter_app/kitchen/models/kitchen_order_model.dart';

// Ported unchanged from kitchen-app/test/kds_board_test.dart.
void main() {
  group('KDS Models & Financial Data Scrubbing', () {
    test('KitchenOrderModel parses successfully with zero financial data', () {
      final json = {
        'id': 'ord-123',
        'order_number': 'ORD-20261010-001',
        'table_id': 'tbl-456',
        'table_number': 5,
        'table_display_name': 'Table 5',
        'source': 'CUSTOMER_QR',
        'status': 'PLACED',
        'placed_at': '2026-10-10T12:00:00Z',
        'elapsed_seconds': 120,
        'version': 1,
        'special_instructions': 'Extra crispy',
        'has_unacknowledged_mods': false,
        'items': [
          {
            'order_item_id': 'oi-1',
            'item_code': 'CB',
            'item_name': 'Chicken Biryani',
            'variant_name': 'Full',
            'original_quantity': 2,
            'active_quantity': 2,
            'item_status': 'ACTIVE',
            'item_notes': 'Less spicy',
          }
        ],
        'unacknowledged_modifications': [],
      };

      final order = KitchenOrderModel.fromJson(json);

      expect(order.id, equals('ord-123'));
      expect(order.orderNumber, equals('ORD-20261010-001'));
      expect(order.tableDisplayName, equals('Table 5'));
      expect(order.status, equals('PLACED'));
      expect(order.items.length, equals(1));
      expect(order.items.first.itemCode, equals('CB'));
      expect(order.items.first.activeQuantity, equals(2));
      expect(order.hasUnacknowledgedMods, isFalse);
    });

    test('KitchenModificationEventModel parses modification diff correctly', () {
      final json = {
        'modification_event_id': 'mod-999',
        'modification_type': 'QUANTITY_INCREASED',
        'item_name': 'Chicken Biryani (Full)',
        'previous_quantity': 2,
        'new_quantity': 3,
        'reason': 'Guest asked for 1 more',
        'created_at': '2026-10-10T12:05:00Z',
      };

      final mod = KitchenModificationEventModel.fromJson(json);

      expect(mod.modificationEventId, equals('mod-999'));
      expect(mod.previousQuantity, equals(2));
      expect(mod.newQuantity, equals(3));
      expect(mod.reason, equals('Guest asked for 1 more'));
    });
  });
}
