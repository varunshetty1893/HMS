import '../config/kds_theme.dart';
import 'package:flutter/material.dart';
import '../models/kitchen_item_model.dart';

class OrderModificationBadge extends StatelessWidget {
  final List<KitchenModificationEventModel> modifications;
  final VoidCallback onAcknowledge;

  const OrderModificationBadge({
    super.key,
    required this.modifications,
    required this.onAcknowledge,
  });

  @override
  Widget build(BuildContext context) {
    if (modifications.isEmpty) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.amber.shade900.withOpacity(0.3),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.amber.shade500, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: Colors.amber.shade400, size: 18),
              const SizedBox(width: 6),
              const Expanded(
                child: Text(
                  'ORDER MODIFIED BY WAITER',
                  style: TextStyle(
                    color: Colors.amber,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ...modifications.map((mod) {
            final isIncrease = mod.newQuantity > mod.previousQuantity;
            final isCancelled = mod.newQuantity == 0;

            String badgeText;
            Color badgeColor;
            if (isCancelled) {
              badgeText = '[- CANCELLED]';
              badgeColor = Colors.red.shade400;
            } else if (isIncrease) {
              badgeText = '[+ ADDED]';
              badgeColor = Colors.green.shade400;
            } else {
              badgeText = '[QTY CHANGED]';
              badgeColor = Colors.amber.shade400;
            }

            return Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                children: [
                  Text(
                    badgeText,
                    style: TextStyle(
                      color: badgeColor,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      '${mod.itemName}: ${mod.previousQuantity} → ${mod.newQuantity} (${mod.reason})',
                      style: const TextStyle(
                        color: KdsTheme.textPrimary,
                        fontSize: 12,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            );
          }),
          const SizedBox(height: 6),
          SizedBox(
            width: double.infinity,
            height: 36,
            child: ElevatedButton.icon(
              onPressed: onAcknowledge,
              icon: const Icon(Icons.check, size: 16),
              label: const Text(
                'ACKNOWLEDGE CHANGE',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.amber.shade600,
                foregroundColor: Colors.black,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
