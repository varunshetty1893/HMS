import 'package:flutter/material.dart';
import '../config/theme.dart';

class OrderModificationBadge extends StatelessWidget {
  final bool hasUnacknowledgedMods;

  const OrderModificationBadge({
    super.key,
    required this.hasUnacknowledgedMods,
  });

  @override
  Widget build(BuildContext context) {
    if (!hasUnacknowledgedMods) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: WaiterTheme.readyAmberBg,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: WaiterTheme.readyAmber, width: 1),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.warning_amber_rounded, size: 14, color: WaiterTheme.readyAmber),
          SizedBox(width: 4),
          Text(
            'MODIFIED',
            style: TextStyle(
              color: WaiterTheme.readyAmber,
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }
}
