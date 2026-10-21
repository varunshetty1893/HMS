import '../config/kds_theme.dart';
import 'package:flutter/material.dart';
import '../models/kitchen_item_model.dart';

class OrderModificationBadge extends StatelessWidget {
  final List<KitchenModificationEventModel> modifications;
  final VoidCallback onAcknowledge;
  final bool isAcknowledging;

  const OrderModificationBadge({
    super.key,
    required this.modifications,
    required this.onAcknowledge,
    this.isAcknowledging = false,
  });

  @override
  Widget build(BuildContext context) {
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
                  'Order updated by waiter',
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
          if (modifications.isEmpty)
            const Text(
              'Update details are being reconciled. Acknowledge to refresh this order safely.',
              style: TextStyle(color: KdsTheme.textSecondary, fontSize: 12),
            )
          else ...[
            _section('Removed', modifications.where((m) => m.newQuantity == 0 || m.modificationType == 'ITEM_CANCELLED').toList(), Colors.red.shade300),
            _section('Added', modifications.where((m) => m.previousQuantity == 0 || m.modificationType == 'ITEM_ADDED').toList(), Colors.green.shade300),
            _section('Quantity or portion changes', modifications.where((m) => m.newQuantity > 0 && m.previousQuantity > 0 && m.modificationType != 'ITEM_ADDED').toList(), Colors.amber.shade200),
          ],
          const SizedBox(height: 6),
          const Text('Ready is disabled until these changes are acknowledged.', style: TextStyle(color: KdsTheme.textSecondary, fontSize: 11)),
          const SizedBox(height: 6),
          SizedBox(
            width: double.infinity,
            height: 36,
            child: ElevatedButton.icon(
              onPressed: isAcknowledging ? null : onAcknowledge,
              icon: isAcknowledging ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.check, size: 16),
              label: Text(
                isAcknowledging ? 'ACKNOWLEDGING…' : 'ACKNOWLEDGE CHANGE',
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

  Widget _section(String heading, List<KitchenModificationEventModel> entries, Color color) {
    if (entries.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(heading, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold)),
        ...entries.map((mod) => Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Text('${mod.itemName}: ${mod.previousQuantity} → ${mod.newQuantity}${mod.reason.isEmpty ? '' : ' · ${mod.reason}'}', maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: KdsTheme.textPrimary, fontSize: 12)),
        )),
      ]),
    );
  }
}
