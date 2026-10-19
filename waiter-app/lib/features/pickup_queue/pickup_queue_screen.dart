import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../core/utils/currency_formatter.dart';
import '../../core/utils/date_formatter.dart';
import '../order_confirmation/order_confirmation_controller.dart';
import '../order_confirmation/order_confirmation_screen.dart';
import 'pickup_queue_controller.dart';

class PickupQueueScreen extends ConsumerWidget {
  const PickupQueueScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(pickupQueueControllerProvider);
    final controller = ref.read(pickupQueueControllerProvider.notifier);
    final confirmations = ref.watch(orderConfirmationControllerProvider);

    ref.listen<OrderConfirmationState>(orderConfirmationControllerProvider,
        (previous, next) {
      if (next.count > (previous?.count ?? 0)) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(
            SnackBar(
              duration: const Duration(seconds: 8),
              content: Text(
                '${next.items.last.tableLabel} wants to order. Confirm guests are seated?',
              ),
              action: SnackBarAction(
                label: 'REVIEW',
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => const OrderConfirmationScreen(),
                    ),
                  );
                },
              ),
            ),
          );
      }
    });

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: Row(
          children: [
            const Text(
              'Food Pass — Ready Orders',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            if (state.readyOrders.isNotEmpty) ...[
              const SizedBox(width: 10),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppTheme.readyColor,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '${state.readyOrders.length}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
              ),
            ],
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => controller.loadReadyOrders(),
          ),
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.how_to_reg),
                tooltip: 'Order Requests',
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => const OrderConfirmationScreen(),
                    ),
                  );
                },
              ),
              if (confirmations.count > 0)
                Positioned(
                  top: 8,
                  right: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: AppTheme.errorColor,
                      shape: BoxShape.circle,
                    ),
                    constraints: const BoxConstraints(
                      minWidth: 16,
                      minHeight: 16,
                    ),
                    child: Text(
                      '${confirmations.count}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          if (confirmations.count > 0)
            Material(
              color: WaiterTheme.readyAmberBg,
              child: InkWell(
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => const OrderConfirmationScreen(),
                    ),
                  );
                },
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  child: Row(
                    children: [
                      const Icon(Icons.notifications_active,
                          color: AppTheme.warningColor),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          confirmations.count == 1
                              ? '1 table is waiting for you to confirm its order'
                              : '${confirmations.count} tables are waiting for you to confirm their orders',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                ),
              ),
            ),
          Expanded(
            child: state.isLoading
                ? const Center(child: CircularProgressIndicator())
                : state.error != null
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(state.error!,
                                style:
                                    const TextStyle(color: AppTheme.errorColor)),
                            const SizedBox(height: 12),
                            ElevatedButton(
                              onPressed: () => controller.loadReadyOrders(),
                              child: const Text('Retry'),
                            ),
                          ],
                        ),
                      )
                    : state.readyOrders.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Icon(Icons.check_circle_outline,
                                    size: 72, color: AppTheme.successColor),
                                const SizedBox(height: 16),
                                const Text(
                                  'All clear! No ready orders.',
                                  style: TextStyle(
                                    color: AppTheme.textPrimary,
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                const Text(
                                  'Orders will appear here when kitchen marks them READY.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                      color: AppTheme.textSecondary, fontSize: 13),
                                ),
                              ],
                            ),
                          )
                        : RefreshIndicator(
                            onRefresh: () => controller.loadReadyOrders(),
                            child: ListView.builder(
                              padding: const EdgeInsets.all(16),
                              itemCount: state.readyOrders.length,
                              itemBuilder: (context, index) {
                                final order = state.readyOrders[index];
                                final isMarkingServed =
                                    state.markingServedIds.contains(order.id);

                                return Container(
                                  margin: const EdgeInsets.only(bottom: 12),
                                  decoration: BoxDecoration(
                                    color: AppTheme.cardColor,
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                      color: AppTheme.readyColor.withOpacity(0.8),
                                      width: 2,
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: AppTheme.readyColor.withOpacity(0.15),
                                        blurRadius: 8,
                                        offset: const Offset(0, 3),
                                      ),
                                    ],
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      // Order header
                                      Container(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 16, vertical: 12),
                                        decoration: BoxDecoration(
                                          color: AppTheme.readyColor.withOpacity(0.1),
                                          borderRadius: const BorderRadius.vertical(
                                              top: Radius.circular(10)),
                                        ),
                                        child: Row(
                                          mainAxisAlignment:
                                              MainAxisAlignment.spaceBetween,
                                          children: [
                                            Row(
                                              children: [
                                                const Icon(Icons.dinner_dining,
                                                    color: AppTheme.readyColor,
                                                    size: 20),
                                                const SizedBox(width: 8),
                                                Text(
                                                  'Order #${order.orderNumber}',
                                                  style: const TextStyle(
                                                    color: AppTheme.readyColor,
                                                    fontWeight: FontWeight.bold,
                                                    fontSize: 16,
                                                  ),
                                                ),
                                              ],
                                            ),
                                            Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.end,
                                              children: [
                                                Container(
                                                  padding: const EdgeInsets.symmetric(
                                                      horizontal: 8, vertical: 3),
                                                  decoration: BoxDecoration(
                                                    color: AppTheme.cardAltColor,
                                                    borderRadius:
                                                        BorderRadius.circular(6),
                                                  ),
                                                  child: Text(
                                                    'Table ${order.tableNumber ?? '?'}',
                                                    style: const TextStyle(
                                                      color: AppTheme.textPrimary,
                                                      fontWeight: FontWeight.bold,
                                                      fontSize: 14,
                                                    ),
                                                  ),
                                                ),
                                                const SizedBox(height: 2),
                                                Text(
                                                  DateFormatter.elapsed(
                                                      order.updatedAt),
                                                  style: const TextStyle(
                                                    color: AppTheme.textMuted,
                                                    fontSize: 11,
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ],
                                        ),
                                      ),
                                      // Items
                                      Padding(
                                        padding: const EdgeInsets.all(16),
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            ...order.items.map((item) {
                                              return Padding(
                                                padding:
                                                    const EdgeInsets.only(bottom: 6),
                                                child: Row(
                                                  children: [
                                                    Container(
                                                      width: 24,
                                                      height: 24,
                                                      alignment: Alignment.center,
                                                      decoration: BoxDecoration(
                                                        color: AppTheme.accentColor
                                                            .withOpacity(0.15),
                                                        borderRadius:
                                                            BorderRadius.circular(6),
                                                      ),
                                                      child: Text(
                                                        '${item.quantity}',
                                                        style: const TextStyle(
                                                          color: AppTheme.accentColor,
                                                          fontWeight: FontWeight.bold,
                                                          fontSize: 13,
                                                        ),
                                                      ),
                                                    ),
                                                    const SizedBox(width: 8),
                                                    Expanded(
                                                      child: Text(
                                                        '${item.itemName}${item.variantName != null ? " (${item.variantName})" : ""}',
                                                        style: const TextStyle(
                                                          color: AppTheme.textPrimary,
                                                          fontSize: 14,
                                                        ),
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              );
                                            }),
                                          ],
                                        ),
                                      ),
                                      // Footer: subtotal + Mark Served
                                      Container(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 16, vertical: 12),
                                        decoration: const BoxDecoration(
                                          border: Border(
                                              top: BorderSide(
                                                  color: AppTheme.borderColor)),
                                        ),
                                        child: Row(
                                          mainAxisAlignment:
                                              MainAxisAlignment.spaceBetween,
                                          children: [
                                            Text(
                                              CurrencyFormatter
                                                  .format(order.subtotal),
                                              style: const TextStyle(
                                                color: AppTheme.textSecondary,
                                                fontSize: 14,
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                            SizedBox(
                                              height: 40,
                                              child: ElevatedButton.icon(
                                                icon: isMarkingServed
                                                    ? const SizedBox(
                                                        width: 16,
                                                        height: 16,
                                                        child:
                                                            CircularProgressIndicator(
                                                          strokeWidth: 2,
                                                          color: Colors.white,
                                                        ),
                                                      )
                                                    : const Icon(
                                                        Icons.check_circle,
                                                        size: 18),
                                                label: Text(isMarkingServed
                                                    ? 'Marking...'
                                                    : 'Mark Served'),
                                                style: ElevatedButton.styleFrom(
                                                  backgroundColor:
                                                      AppTheme.successColor,
                                                  foregroundColor: Colors.white,
                                                ),
                                                onPressed: isMarkingServed
                                                    ? null
                                                    : () =>
                                                        controller.markServed(order.id),
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              },
                            ),
                          ),
          ),
        ],
      ),
    );
  }
}
