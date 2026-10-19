import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../core/utils/currency_formatter.dart';
import 'order_confirmation_controller.dart';

/// First QR order on an empty table: confirm that guests are seated, or reject.
class OrderConfirmationScreen extends ConsumerWidget {
  const OrderConfirmationScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(orderConfirmationControllerProvider);
    final controller = ref.read(orderConfirmationControllerProvider.notifier);

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: const Text(
          'Order Requests',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: () => controller.load(),
          ),
        ],
      ),
      body: Column(
        children: [
          if (state.error != null)
            Container(
              width: double.infinity,
              color: WaiterTheme.errorRedBg,
              padding: const EdgeInsets.all(12),
              child: Text(
                state.error!,
                style: const TextStyle(color: AppTheme.errorColor),
              ),
            ),
          Expanded(
            child: state.isLoading
                ? const Center(child: CircularProgressIndicator())
                : state.items.isEmpty
                    ? const _EmptyState()
                    : ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: state.items.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final item = state.items[index];
                          return _RequestCard(
                            item: item,
                            secondsLeft: state.secondsLeft(item),
                            busy: state.busyIds.contains(item.order.id),
                            onConfirm: () => controller.confirm(item.order.id),
                            onReject: () => _askReject(context, controller, item),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }

  Future<void> _askReject(
    BuildContext context,
    OrderConfirmationController controller,
    PendingConfirmation item,
  ) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Reject request from ${item.tableLabel}?'),
        content: const Text(
          'Use this when nobody is sitting at the table. The guest is told to '
          'ask a waiter for help and the order never reaches the kitchen.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Keep'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text(
              'Reject',
              style: TextStyle(color: AppTheme.errorColor),
            ),
          ),
        ],
      ),
    );
    if (ok == true) {
      await controller.reject(item.order.id, reason: 'No guests at the table');
    }
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: const [
          Icon(Icons.check_circle_outline,
              size: 72, color: AppTheme.successColor),
          SizedBox(height: 16),
          Text(
            'No orders waiting for confirmation.',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

class _RequestCard extends StatelessWidget {
  final PendingConfirmation item;
  final int secondsLeft;
  final bool busy;
  final VoidCallback onConfirm;
  final VoidCallback onReject;

  const _RequestCard({
    required this.item,
    required this.secondsLeft,
    required this.busy,
    required this.onConfirm,
    required this.onReject,
  });

  String get _countdown {
    final m = secondsLeft ~/ 60;
    final s = (secondsLeft % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    final order = item.order;
    final urgent = secondsLeft <= 30;
    return Card(
      color: AppTheme.cardColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: urgent ? AppTheme.warningColor : AppTheme.borderColor,
          width: urgent ? 1.5 : 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${item.tableLabel} wants to order',
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: urgent
                        ? WaiterTheme.readyAmberBg
                        : AppTheme.cardAltColor,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    _countdown,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: urgent
                          ? AppTheme.warningColor
                          : AppTheme.textSecondary,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Order #${order.orderNumber} • ${CurrencyFormatter.format(order.subtotal)}',
              style: const TextStyle(color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 10),
            ...order.items.map(
              (i) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(
                  '${i.quantity}x ${i.itemName}'
                  '${i.variantName != null ? ' (${i.variantName})' : ''}',
                ),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Is anyone sitting at this table?',
              style: TextStyle(
                fontSize: 12,
                color: AppTheme.textSecondary,
                fontStyle: FontStyle.italic,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: busy ? null : onReject,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.errorColor,
                    ),
                    child: const Text('Reject'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 2,
                  child: ElevatedButton.icon(
                    onPressed: busy || secondsLeft == 0 ? null : onConfirm,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.successColor,
                      foregroundColor: Colors.white,
                    ),
                    icon: busy
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Icon(Icons.check),
                    label: const Text('Guests are seated'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
