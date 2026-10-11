import 'package:flutter/material.dart';
import '../config/theme.dart';

class StatusBadge extends StatelessWidget {
  final String status;
  final bool compact;

  const StatusBadge({
    super.key,
    required this.status,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color fg;
    String label;

    switch (status.toUpperCase()) {
      case 'AVAILABLE':
        bg = WaiterTheme.availableGreenBg;
        fg = WaiterTheme.availableGreen;
        label = 'AVAILABLE';
        break;
      case 'OCCUPIED':
        bg = WaiterTheme.occupiedBlueBg;
        fg = WaiterTheme.occupiedBlue;
        label = 'OCCUPIED';
        break;
      case 'PLACED':
        bg = const Color(0xFF334155);
        fg = const Color(0xFFCBD5E1);
        label = 'PLACED';
        break;
      case 'ACCEPTED':
        bg = const Color(0xFF1E3A8A);
        fg = const Color(0xFF60A5FA);
        label = 'ACCEPTED';
        break;
      case 'PREPARING':
        bg = const Color(0xFF1E3A8A);
        fg = const Color(0xFF93C5FD);
        label = 'PREPARING';
        break;
      case 'READY':
        bg = WaiterTheme.readyAmberBg;
        fg = WaiterTheme.readyAmber;
        label = 'READY FOR PICKUP';
        break;
      case 'SERVED':
        bg = WaiterTheme.availableGreenBg;
        fg = WaiterTheme.availableGreen;
        label = 'SERVED';
        break;
      case 'CANCELLED':
        bg = WaiterTheme.errorRedBg;
        fg = WaiterTheme.errorRed;
        label = 'CANCELLED';
        break;
      case 'REJECTED':
        bg = WaiterTheme.errorRedBg;
        fg = WaiterTheme.errorRed;
        label = 'REJECTED';
        break;
      default:
        bg = WaiterTheme.surfaceVariant;
        fg = WaiterTheme.textSecondary;
        label = status;
    }

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 6 : 10,
        vertical: compact ? 3 : 5,
      ),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: fg.withOpacity(0.4), width: 1),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: fg,
          fontSize: compact ? 11 : 12,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
        ),
      ),
    );
  }
}
