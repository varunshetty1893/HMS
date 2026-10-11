import 'package:flutter_test/flutter_test.dart';
import 'package:waiter_app/models/table_model.dart';
import 'package:waiter_app/models/order_model.dart';
import 'package:waiter_app/features/order_entry/order_entry_controller.dart';
import 'package:waiter_app/models/menu_search_result.dart';
import 'package:waiter_app/models/bill_model.dart';

void main() {
  group('TableModel serialization', () {
    test('parses AVAILABLE table correctly', () {
      final json = {
        'id': 'table-001',
        'table_number': 5,
        'capacity': 4,
        'status': 'AVAILABLE',
        'display_name': 'Window Booth',
        'location_description': 'Near main entrance',
        'active_orders_count': 0,
        'ready_orders_count': 0,
      };

      final table = TableModel.fromJson(json);

      expect(table.id, equals('table-001'));
      expect(table.tableNumber, equals(5));
      expect(table.capacity, equals(4));
      expect(table.status, equals('AVAILABLE'));
      expect(table.isAvailable, isTrue);
      expect(table.isOccupied, isFalse);
      expect(table.displayName, equals('Window Booth'));
      expect(table.activeOrdersCount, equals(0));
    });

    test('parses OCCUPIED table with ready orders', () {
      final json = {
        'id': 'table-002',
        'table_number': 12,
        'capacity': 6,
        'status': 'OCCUPIED',
        'display_name': null,
        'location_description': null,
        'active_orders_count': 3,
        'ready_orders_count': 1,
      };

      final table = TableModel.fromJson(json);

      expect(table.isOccupied, isTrue);
      expect(table.isAvailable, isFalse);
      expect(table.activeOrdersCount, equals(3));
      expect(table.readyOrdersCount, equals(1));
    });
  });

  group('OrderModel serialization', () {
    test('parses READY order correctly', () {
      final json = {
        'id': 'order-001',
        'order_number': 'ORD-20241001-001',
        'table_id': 'table-001',
        'table_number': 5,
        'status': 'READY',
        'source': 'WAITER',
        'subtotal': 450.0,
        'version': 2,
        'has_unacknowledged_mods': false,
        'created_at': '2024-10-01T10:00:00Z',
        'updated_at': '2024-10-01T10:15:00Z',
        'served_at': null,
        'items': [
          {
            'id': 'item-001',
            'menu_item_id': 'menu-001',
            'variant_id': 'var-001',
            'item_name': 'Chicken Biryani',
            'variant_name': 'Half',
            'quantity': 2,
            'unit_price': 225.0,
            'subtotal': 450.0,
            'special_instructions': null,
          }
        ],
      };

      final order = OrderModel.fromJson(json);

      expect(order.id, equals('order-001'));
      expect(order.orderNumber, equals('ORD-20241001-001'));
      expect(order.status, equals('READY'));
      expect(order.source, equals('WAITER'));
      expect(order.subtotal, equals(450.0));
      expect(order.version, equals(2));
      expect(order.hasUnacknowledgedMods, isFalse);
      expect(order.items.length, equals(1));
      expect(order.items.first.itemName, equals('Chicken Biryani'));
      expect(order.items.first.quantity, equals(2));
      expect(order.items.first.unitPrice, equals(225.0));
      expect(order.items.first.subtotal, equals(450.0));
    });

    test('parses order with has_unacknowledged_mods = true', () {
      final json = {
        'id': 'order-002',
        'order_number': 'ORD-20241001-002',
        'table_id': 'table-002',
        'table_number': 8,
        'status': 'PREPARING',
        'source': 'CUSTOMER',
        'subtotal': 320.0,
        'version': 3,
        'has_unacknowledged_mods': true,
        'created_at': '2024-10-01T11:00:00Z',
        'updated_at': '2024-10-01T11:10:00Z',
        'served_at': null,
        'items': [],
      };

      final order = OrderModel.fromJson(json);
      expect(order.hasUnacknowledgedMods, isTrue);
      expect(order.status, equals('PREPARING'));
    });
  });

  group('Cart math in OrderEntryController', () {
    test('CartItem.lineTotal = unitPrice * quantity', () {
      final variant = MenuVariantResult(
        id: 'var-001',
        name: 'Full',
        price: 350.0,
      );
      final item = MenuItemResult(
        id: 'menu-001',
        name: 'Mutton Biryani',
        shortCode: 'MB-F',
        categoryName: 'Biryani',
        variants: [variant],
      );

      final cartItem = CartItem(item: item, variant: variant, quantity: 3);

      expect(cartItem.lineTotal, equals(1050.0));
      expect(cartItem.cartKey, equals('menu-001__var-001'));
    });

    test('multiple CartItems total correctly', () {
      final v1 = MenuVariantResult(id: 'v1', name: 'Half', price: 180.0);
      final v2 = MenuVariantResult(id: 'v2', name: 'Full', price: 350.0);
      final item = MenuItemResult(
          id: 'i1', name: 'Biryani', shortCode: 'BR-H', categoryName: 'Main', variants: [v1, v2]);

      final ci1 = CartItem(item: item, variant: v1, quantity: 2);
      final ci2 = CartItem(item: item, variant: v2, quantity: 1);

      expect(ci1.lineTotal + ci2.lineTotal, equals(710.0)); // 360 + 350
    });

    test('CartItem.lineTotal updates when quantity changes', () {
      final v = MenuVariantResult(id: 'v1', name: 'Reg', price: 100.0);
      final item = MenuItemResult(
          id: 'i1', name: 'Lassi', shortCode: 'LS-R', categoryName: 'Drinks', variants: [v]);
      final ci = CartItem(item: item, variant: v, quantity: 1);

      expect(ci.lineTotal, equals(100.0));
      ci.quantity = 4;
      expect(ci.lineTotal, equals(400.0));
    });
  });

  group('TableModel status helpers', () {
    TableModel makeTable(String status) {
      return TableModel.fromJson({
        'id': 'x',
        'table_number': 1,
        'capacity': 2,
        'status': status,
        'active_orders_count': 0,
        'ready_orders_count': 0,
      });
    }

    test('AVAILABLE isAvailable=true, isOccupied=false', () {
      final t = makeTable('AVAILABLE');
      expect(t.isAvailable, isTrue);
      expect(t.isOccupied, isFalse);
    });

    test('OCCUPIED isAvailable=false, isOccupied=true', () {
      final t = makeTable('OCCUPIED');
      expect(t.isAvailable, isFalse);
      expect(t.isOccupied, isTrue);
    });

    test('RESERVED isAvailable=false, isOccupied=false', () {
      final t = makeTable('RESERVED');
      expect(t.isAvailable, isFalse);
      expect(t.isOccupied, isFalse);
    });
  });

  group('BillModel & TableBillModel serialization', () {
    test('parses BillModel correctly', () {
      final json = {
        'id': 'bill-001',
        'bill_number': 'INV-20261011-0001',
        'table_session_id': 'sess-001',
        'table_id': 'tbl-001',
        'table_number': 5,
        'table_display_name': 'Window Booth',
        'status': 'ISSUED',
        'subtotal_amount': 360.0,
        'discount_amount': 0.0,
        'taxable_amount': 360.0,
        'cgst_rate_snapshot': 2.5,
        'cgst_amount': 9.0,
        'sgst_rate_snapshot': 2.5,
        'sgst_amount': 9.0,
        'service_charge_amount': 0.0,
        'rounding_adjustment': 0.0,
        'grand_total': 378.0,
        'generated_by_name': 'Karthik',
        'generated_at': '2026-10-11T12:00:00Z',
        'line_items': [
          {
            'order_number': 'ORD-001',
            'item_code': 'CB',
            'item_name': 'Chicken Biryani',
            'variant_name': 'Full',
            'unit': 'PORTION',
            'quantity_billed': 2,
            'unit_price_snapshot': 180.0,
            'line_total': 360.0,
          }
        ],
      };

      final bill = BillModel.fromJson(json);

      expect(bill.id, equals('bill-001'));
      expect(bill.billNumber, equals('INV-20261011-0001'));
      expect(bill.status, equals('ISSUED'));
      expect(bill.isPaid, isFalse);
      expect(bill.subtotalAmount, equals(360.0));
      expect(bill.cgstAmount, equals(9.0));
      expect(bill.sgstAmount, equals(9.0));
      expect(bill.grandTotal, equals(378.0));
      expect(bill.lineItems.length, equals(1));
      expect(bill.lineItems.first.itemName, equals('Chicken Biryani'));
      expect(bill.lineItems.first.lineTotal, equals(360.0));
    });

    test('TableBillModel canGenerateBill returns true only when orders are served and not already billed', () {
      final json = {
        'table_number': 5,
        'table_id': 'tbl-001',
        'table_session_id': 'sess-001',
        'session_code': 'TS-001',
        'has_unaccepted_placed_orders': false,
        'has_unserved_orders': false,
        'bill_status': 'NOT_GENERATED',
        'preview_line_items': [],
        'preview_subtotal': 360.0,
        'preview_grand_total': 378.0,
      };

      final tableBill = TableBillModel.fromJson(json);

      expect(tableBill.canGenerateBill, isTrue);
      expect(tableBill.isBillIssued, isFalse);
    });

    test('TableBillModel canGenerateBill returns false when unserved orders remain', () {
      final json = {
        'table_number': 5,
        'table_id': 'tbl-001',
        'table_session_id': 'sess-001',
        'session_code': 'TS-001',
        'has_unaccepted_placed_orders': false,
        'has_unserved_orders': true,
        'bill_status': 'NOT_GENERATED',
        'preview_line_items': [],
      };

      final tableBill = TableBillModel.fromJson(json);

      expect(tableBill.canGenerateBill, isFalse);
    });
  });
}
