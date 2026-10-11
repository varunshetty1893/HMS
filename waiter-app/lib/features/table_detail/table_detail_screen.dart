import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../core/utils/currency_formatter.dart';
import '../../core/utils/date_formatter.dart';
import '../../models/order_model.dart';
import '../../models/table_model.dart';
import '../../widgets/limit_progress_bar.dart';
import '../../widgets/modification_badge.dart';
import '../../widgets/status_badge.dart';
import '../billing/bill_preview_screen.dart';
import '../order_entry/manual_order_entry_screen.dart';
import '../order_modification/order_cancel_dialog.dart';
import '../order_modification/order_edit_screen.dart';
import 'table_detail_controller.dart';

class TableDetailScreen extends ConsumerWidget {
  final TableModel table;

  const TableDetailScreen({
    Key? key,
    required this.table,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(tableDetailControllerProvider(table.id));
    final controller = ref.read(tableDetailControllerProvider(table.id).notifier);
    final detail = state.sessionDetail;

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: Text('Table ${table.tableNumber} Detail'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => controller.loadSessionDetail(),
          ),
        ],
      ),
      body: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : state.error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(state.error!,
                          style: const TextStyle(color: AppTheme.errorColor)),
                      const SizedBox(height: 12),
                      ElevatedButton(
                        onPressed: () => controller.loadSessionDetail(),
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : detail == null
                  ? const Center(child: Text('Session data unavailable'))
                  : Column(
                      children: [
                        // Header card with table info & limit headroom
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: const BoxDecoration(
                            color: AppTheme.cardColor,
                            border: Border(
                              bottom: BorderSide(color: AppTheme.borderColor),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Row(
                                    children: [
                                      Text(
                                        'Table ${detail.table.tableNumber}',
                                        style: const TextStyle(
                                          fontSize: 20,
                                          fontWeight: FontWeight.bold,
                                          color: AppTheme.textPrimary,
                                        ),
                                      ),
                                      if (detail.table.displayName != null)
                                        Text(
                                          ' (${detail.table.displayName})',
                                          style: const TextStyle(
                                            fontSize: 16,
                                            color: AppTheme.textSecondary,
                                          ),
                                        ),
                                    ],
                                  ),
                                  StatusBadge(status: detail.table.status),
                                ],
                              ),
                              const SizedBox(height: 12),
                              LimitProgressBar(
                                currentExposure: detail.currentExposure,
                                limit: detail.unpaidSpendLimit,
                                remainingLimit: detail.remainingLimit,
                              ),
                            ],
                          ),
                        ),
                        // Active Orders list
                        Expanded(
                          child: detail.activeOrders.isEmpty
                              ? Center(
                                  child: Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      const Icon(Icons.receipt_long,
                                          size: 48,
                                          color: AppTheme.textSecondary),
                                      const SizedBox(height: 12),
                                      const Text(
                                        'No active orders on this table',
                                        style: TextStyle(
                                            color: AppTheme.textSecondary,
                                            fontSize: 15),
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        table.isAvailable
                                            ? 'Table is available for new guests'
                                            : 'All orders have been served or paid',
                                        style: const TextStyle(
                                            color: AppTheme.textMuted,
                                            fontSize: 12),
                                      ),
                                    ],
                                  ),
                                )
                              : ListView.builder(
                                  padding: const EdgeInsets.all(16),
                                  itemCount: detail.activeOrders.length,
                                  itemBuilder: (context, index) {
                                    final order = detail.activeOrders[index];
                                    return _buildOrderCard(
                                        context, order, controller);
                                  },
                                ),
                        ),
                        // Bottom Action Bar
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: const BoxDecoration(
                            color: AppTheme.surfaceColor,
                            border: Border(
                              top: BorderSide(color: AppTheme.borderColor),
                            ),
                          ),
                          child: Row(
                            children: [
                              Expanded(
                                flex: 3,
                                child: SizedBox(
                                  height: 50,
                                  child: ElevatedButton.icon(
                                    icon: const Icon(Icons.add_shopping_cart, size: 20),
                                    label: const Text(
                                      'Take Order',
                                      style: TextStyle(
                                          fontSize: 15, fontWeight: FontWeight.bold),
                                    ),
                                    onPressed: () async {
                                      final created =
                                          await Navigator.of(context).push<bool>(
                                        MaterialPageRoute(
                                          builder: (_) => ManualOrderEntryScreen(
                                            table: detail.table,
                                            remainingLimit: detail.remainingLimit,
                                          ),
                                        ),
                                      );
                                      if (created == true) {
                                        controller.loadSessionDetail();
                                      }
                                    },
                                  ),
                                ),
                              ),
                              if (detail.activeOrders.isNotEmpty) ...[
                                const SizedBox(width: 12),
                                Expanded(
                                  flex: 3,
                                  child: SizedBox(
                                    height: 50,
                                    child: OutlinedButton.icon(
                                      icon: const Icon(Icons.receipt_long, size: 20),
                                      label: const Text(
                                        'Bill & Settle',
                                        style: TextStyle(
                                            fontSize: 15, fontWeight: FontWeight.bold),
                                      ),
                                      style: OutlinedButton.styleFrom(
                                        foregroundColor: AppTheme.accentColor,
                                        side: const BorderSide(color: AppTheme.accentColor, width: 1.5),
                                      ),
                                      onPressed: () async {
                                        await Navigator.of(context).push(
                                          MaterialPageRoute(
                                            builder: (_) => BillPreviewScreen(
                                              tableNumber: detail.table.tableNumber,
                                              tableDisplayName: detail.table.displayName,
                                            ),
                                          ),
                                        );
                                        controller.loadSessionDetail();
                                      },
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ],
                    ),
    );
  }

  Widget _buildOrderCard(
    BuildContext context,
    OrderModel order,
    TableDetailController controller,
  ) {
    final canEdit = order.status == 'PLACED' ||
        order.status == 'ACCEPTED' ||
        order.status == 'PREPARING';
    final canCancel = order.status == 'PLACED' || order.status == 'ACCEPTED';
    final canServe = order.status == 'READY';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: order.status == 'READY'
              ? AppTheme.readyColor.withOpacity(0.8)
              : AppTheme.borderColor,
          width: order.status == 'READY' ? 2 : 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Order Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: AppTheme.cardAltColor,
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(12)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Text(
                      '#${order.orderNumber}',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: order.source == 'WAITER'
                            ? AppTheme.accentColor.withOpacity(0.2)
                            : Colors.blue.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        order.source,
                        style: TextStyle(
                          color: order.source == 'WAITER'
                              ? AppTheme.accentColor
                              : Colors.lightBlueAccent,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    if (order.hasUnacknowledgedMods) ...[
                      const SizedBox(width: 6),
                      const ModificationBadge(),
                    ],
                  ],
                ),
                StatusBadge(status: order.status),
              ],
            ),
          ),
          // Items
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ...order.items.map((item) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            '${item.quantity}x ${item.itemName}${item.variantName != null ? ' (${item.variantName})' : ''}',
                            style: const TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 14,
                            ),
                          ),
                        ),
                        Text(
                          CurrencyFormatter.format(item.subtotal),
                          style: const TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  );
                }),
                const Divider(color: AppTheme.borderColor),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      DateFormatter.formatTime(order.createdAt),
                      style: const TextStyle(
                        color: AppTheme.textMuted,
                        fontSize: 12,
                      ),
                    ),
                    Text(
                      'Subtotal: ${CurrencyFormatter.format(order.subtotal)}',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: AppTheme.accentColor,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          // Action Buttons
          if (canEdit || canCancel || canServe)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: AppTheme.borderColor)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (canCancel) ...[
                    OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.errorColor,
                        side: const BorderSide(color: AppTheme.errorColor),
                      ),
                      onPressed: () async {
                        final reason = await OrderCancelDialog.show(
                          context,
                          orderId: order.id,
                          orderNumber: order.orderNumber,
                        );
                        if (reason != null) {
                          await controller.cancelOrder(order.id, reason);
                        }
                      },
                      child: const Text('Cancel Order'),
                    ),
                    const SizedBox(width: 8),
                  ],
                  if (canEdit) ...[
                    OutlinedButton(
                      onPressed: () async {
                        final modified =
                            await Navigator.of(context).push<bool>(
                          MaterialPageRoute(
                            builder: (_) => OrderEditScreen(order: order),
                          ),
                        );
                        if (modified == true) {
                          controller.loadSessionDetail();
                        }
                      },
                      child: const Text('Edit Items'),
                    ),
                    const SizedBox(width: 8),
                  ],
                  if (canServe) ...[
                    ElevatedButton.icon(
                      icon: const Icon(Icons.check_circle_outline, size: 18),
                      label: const Text('Mark Served'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.readyColor,
                        foregroundColor: Colors.white,
                      ),
                      onPressed: () async {
                        await controller.markOrderServed(order.id);
                      },
                    ),
                  ],
                ],
              ),
            ),
        ],
      ),
    );
  }
}
