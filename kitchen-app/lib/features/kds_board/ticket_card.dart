import 'package:flutter/material.dart';
import '../../config/theme.dart';
import '../../core/utils/time_formatter.dart';
import '../../models/kitchen_order_model.dart';
import '../../widgets/order_modification_badge.dart';

class TicketCard extends StatelessWidget {
  final KitchenOrderModel order;
  final VoidCallback onAccept;
  final VoidCallback onReject;
  final VoidCallback onStartPreparing;
  final VoidCallback onMarkReady;
  final VoidCallback onAcknowledgeModifications;

  const TicketCard({
    super.key,
    required this.order,
    required this.onAccept,
    required this.onReject,
    required this.onStartPreparing,
    required this.onMarkReady,
    required this.onAcknowledgeModifications,
  });

  @override
  Widget build(BuildContext context) {
    final timerColor = TimeFormatter.getElapsedColor(order.placedAt);
    final isPlaced = order.status == 'PLACED';
    final isAccepted = order.status == 'ACCEPTED';
    final isPreparing = order.status == 'PREPARING';
    final isReady = order.status == 'READY';

    return Card(
      color: KdsTheme.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: order.hasUnacknowledgedMods
              ? Colors.amber.shade500
              : isPlaced
                  ? KdsTheme.placedColor
                  : KdsTheme.border,
          width: isPlaced || order.hasUnacknowledgedMods ? 2 : 1,
        ),
      ),
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: Table badge, Order #, Elapsed timer
            Row(
              mainAxisAlignment: MainAxisAlignment.between,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: KdsTheme.placedColor.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: KdsTheme.placedColor.withOpacity(0.5)),
                      ),
                      child: Text(
                        order.tableDisplayName,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '#${order.orderNumber}',
                      style: const TextStyle(
                        color: KdsTheme.textSecondary,
                        fontSize: 12,
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                // Elapsed Timer
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: timerColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.timer_outlined, color: timerColor, size: 14),
                      const SizedBox(width: 4),
                      Text(
                        TimeFormatter.formatElapsed(order.placedAt),
                        style: TextStyle(
                          color: timerColor,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            const SizedBox(height: 10),

            // Modification Alert Banner (if any)
            if (order.hasUnacknowledgedMods && order.unacknowledgedModifications.isNotEmpty)
              OrderModificationBadge(
                modifications: order.unacknowledgedModifications,
                onAcknowledge: onAcknowledgeModifications,
              ),

            // Special instructions (if any)
            if (order.specialInstructions != null && order.specialInstructions!.isNotEmpty)
              Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.white12),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline, color: Colors.amber, size: 14),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        order.specialInstructions!,
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 12,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

            // Line items list (zero financial fields)
            ...order.items.map((item) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        color: const Color(0xFF334155),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        '${item.activeQuantity}x',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                item.itemName,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(width: 6),
                              Text(
                                '(${item.variantName})',
                                style: const TextStyle(
                                  color: KdsTheme.textSecondary,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                          if (item.itemNotes != null && item.itemNotes!.isNotEmpty)
                            Text(
                              'Note: "${item.itemNotes}"',
                              style: const TextStyle(
                                color: Colors.amberAccent,
                                fontSize: 11,
                                fontStyle: FontStyle.italic,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }),

            const SizedBox(height: 14),

            // Action Buttons
            if (isPlaced)
              Row(
                children: [
                  Expanded(
                    flex: 1,
                    child: OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.redAccent,
                        side: const BorderSide(color: Colors.redAccent),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      onPressed: onReject,
                      child: const Text('Reject', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    flex: 2,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: KdsTheme.placedColor,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      onPressed: onAccept,
                      child: const Text('Accept Order', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                ],
              )
            else if (isAccepted)
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: KdsTheme.preparingColor,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  onPressed: onStartPreparing,
                  icon: const Icon(Icons.soup_kitchen, size: 18),
                  label: const Text('Start Preparing', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              )
            else if (isPreparing)
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: order.hasUnacknowledgedMods
                        ? Colors.grey.shade700
                        : KdsTheme.readyColor,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  onPressed: order.hasUnacknowledgedMods ? null : onMarkReady,
                  icon: const Icon(Icons.check_circle_outline, size: 18),
                  label: Text(
                    order.hasUnacknowledgedMods ? 'Ack Mods Before Ready' : 'Mark Ready for Pickup',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
              )
            else if (isReady)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 10),
                decoration: BoxDecoration(
                  color: KdsTheme.readyColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: KdsTheme.readyColor),
                ),
                alignment: Alignment.center,
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.notifications_active, color: KdsTheme.readyColor, size: 16),
                    SizedBox(width: 6),
                    Text(
                      'Ready for Waiter Pickup',
                      style: TextStyle(
                        color: KdsTheme.readyColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
