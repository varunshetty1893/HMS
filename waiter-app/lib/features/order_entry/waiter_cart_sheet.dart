import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../core/utils/currency_formatter.dart';
import '../../models/table_model.dart';
import '../floor_grid/floor_grid_controller.dart';
import 'order_entry_controller.dart';

class WaiterCartSheet extends ConsumerStatefulWidget {
  final TableModel table;
  final double remainingLimit;

  const WaiterCartSheet({
    Key? key,
    required this.table,
    required this.remainingLimit,
  }) : super(key: key);

  @override
  ConsumerState<WaiterCartSheet> createState() => _WaiterCartSheetState();
}

class _WaiterCartSheetState extends ConsumerState<WaiterCartSheet> {
  final _notesController = TextEditingController();

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(orderEntryControllerProvider);
    final controller = ref.read(orderEntryControllerProvider.notifier);
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    // Projected exposure after placing this cart
    final projectedExposure =
        (widget.remainingLimit >= 5000 ? 0 : (5000 - widget.remainingLimit)) +
            state.cartTotal;
    const exceedsLimit = false; // waiter ke liye table spend limit nahi

    return Container(
      margin: EdgeInsets.only(bottom: bottomInset),
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.85,
      ),
      decoration: const BoxDecoration(
        color: AppTheme.surfaceColor,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        border: Border(top: BorderSide(color: AppTheme.borderColor)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle bar
          Container(
            margin: const EdgeInsets.only(top: 12),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: AppTheme.textMuted,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          // Header
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Cart Review',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    Text(
                      'Table ${widget.table.tableNumber}',
                      style: const TextStyle(
                          color: AppTheme.textSecondary, fontSize: 13),
                    ),
                  ],
                ),
                TextButton(
                  onPressed: () {
                    controller.clearCart();
                    Navigator.of(context).pop(false);
                  },
                  child: const Text('Clear',
                      style: TextStyle(color: AppTheme.errorColor)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          // Cart items list
          Flexible(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: state.cartItems.length,
              itemBuilder: (context, index) {
                final ci = state.cartItems[index];
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.cardColor,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.borderColor),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              '${ci.item.name}${ci.variant.name != null ? " • ${ci.variant.name}" : ""}',
                              style: const TextStyle(
                                color: AppTheme.textPrimary,
                                fontWeight: FontWeight.w600,
                                fontSize: 14,
                              ),
                            ),
                          ),
                          Text(
                            CurrencyFormatter.format(ci.lineTotal),
                            style: const TextStyle(
                              color: AppTheme.accentColor,
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            '${CurrencyFormatter.format(ci.variant.price)} each',
                            style: const TextStyle(
                                color: AppTheme.textSecondary, fontSize: 12),
                          ),
                          Row(
                            children: [
                              _qtyButton(
                                icon: Icons.remove,
                                onTap: () => controller.updateCartQuantity(
                                    ci.cartKey, ci.quantity - 1),
                              ),
                              Padding(
                                padding:
                                    const EdgeInsets.symmetric(horizontal: 12),
                                child: Text(
                                  '${ci.quantity}',
                                  style: const TextStyle(
                                    color: AppTheme.textPrimary,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 16,
                                  ),
                                ),
                              ),
                              _qtyButton(
                                icon: Icons.add,
                                onTap: () => controller.updateCartQuantity(
                                    ci.cartKey, ci.quantity + 1),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
          // Special notes
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _notesController,
              maxLines: 2,
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14),
              decoration: InputDecoration(
                hintText: 'Special request notes for kitchen (optional)...',
                filled: true,
                fillColor: AppTheme.cardColor,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppTheme.borderColor),
                ),
              ),
            ),
          ),
          // Summary + Send button
          Container(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AppTheme.borderColor)),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '${state.cartItemCount} items',
                      style: const TextStyle(
                          color: AppTheme.textSecondary, fontSize: 14),
                    ),
                    Text(
                      CurrencyFormatter.format(state.cartTotal),
                      style: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (state.submitError != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      state.submitError!,
                      style: const TextStyle(
                          color: AppTheme.errorColor, fontSize: 12),
                    ),
                  ),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton.icon(
                    icon: state.isSubmitting
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.send),
                    label: Text(
                      state.isSubmitting ? 'Sending...' : 'Send to Kitchen',
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: exceedsLimit
                          ? AppTheme.textMuted
                          : AppTheme.accentColor,
                      foregroundColor: Colors.white,
                      disabledBackgroundColor: AppTheme.textMuted,
                    ),
                    onPressed: exceedsLimit || state.isSubmitting
                        ? null
                        : () async {
                            final controller =
                                ref.read(orderEntryControllerProvider.notifier);
                            final success = await controller.submitOrder(
                              table: widget.table,
                              specialRequestNotes: _notesController.text,
                            );
                            if (success && mounted) {
                              // Refresh floor grid immediately (don't rely only on WebSocket)
                              ref
                                  .read(floorGridControllerProvider.notifier)
                                  .loadTables(silent: true);
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Order sent to kitchen! ✓'),
                                  backgroundColor: AppTheme.successColor,
                                ),
                              );
                              Navigator.of(context).pop(true);
                            }
                          },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _qtyButton({required IconData icon, required VoidCallback onTap}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: AppTheme.cardAltColor,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: AppTheme.borderColor),
        ),
        child: Icon(icon, size: 18, color: AppTheme.accentColor),
      ),
    );
  }
}
