import 'package:flutter/material.dart';
import '../models/kitchen_order_model.dart';

/// Red, impossible-to-miss strip listing recently cancelled orders.
/// The cook must tap "Got it" for each one (dismissal is per device, in memory).
class CancellationAlertBanner extends StatelessWidget {
  final List<KitchenCancellationAlert> alerts;
  final void Function(String orderId) onDismiss;

  const CancellationAlertBanner({
    super.key,
    required this.alerts,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    if (alerts.isEmpty) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      color: Colors.red.shade900,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      child: Column(
        children: alerts.map((a) {
          final by = a.forced
              ? 'Force-cancelled by ${a.cancelledByRole ?? 'staff'}'
              : 'Cancelled by ${a.cancelledByRole ?? 'staff'}';
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.cancel, color: Colors.white, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${a.headline} - #${a.orderNumber} (${a.tableName})',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                          fontSize: 14,
                        ),
                      ),
                      Text(
                        [
                          by,
                          if (a.reason != null && a.reason!.isNotEmpty) a.reason!,
                        ].join(' - '),
                        style: const TextStyle(color: Colors.white70, fontSize: 12),
                      ),
                      if (a.items.isNotEmpty)
                        Text(
                          a.items.join(', '),
                          style: const TextStyle(color: Colors.white70, fontSize: 12),
                        ),
                    ],
                  ),
                ),
                TextButton(
                  style: TextButton.styleFrom(foregroundColor: Colors.white),
                  onPressed: () => onDismiss(a.orderId),
                  child: const Text('Got it'),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}
