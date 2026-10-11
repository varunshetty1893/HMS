import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../core/utils/currency_formatter.dart';

class LimitProgressBar extends StatelessWidget {
  final double currentExposure;
  final double limit;
  final double remainingLimit;
  final double cartAddition;

  const LimitProgressBar({
    super.key,
    required this.currentExposure,
    required this.limit,
    required this.remainingLimit,
    this.cartAddition = 0.0,
  });

  @override
  Widget build(BuildContext context) {
    final effective = (currentExposure + cartAddition).clamp(0.0, limit * 1.05);
    final progress = limit > 0 ? (effective / limit).clamp(0.0, 1.0) : 0.0;
    final remaining = (limit - effective).clamp(0.0, limit);

    Color barColor = AppTheme.successColor;
    if (progress >= 0.9) {
      barColor = AppTheme.errorColor;
    } else if (progress >= 0.6) {
      barColor = AppTheme.readyColor;
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                const Text(
                  'Spend: ',
                  style: TextStyle(
                    color: AppTheme.textMuted,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  CurrencyFormatter.format(effective),
                  style: const TextStyle(
                    color: AppTheme.textPrimary,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  ' / ${CurrencyFormatter.format(limit)}',
                  style: const TextStyle(
                    color: AppTheme.textMuted,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
            Text(
              '${CurrencyFormatter.format(remaining)} left',
              style: TextStyle(
                color: barColor,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: progress,
            backgroundColor: WaiterTheme.surfaceVariant,
            valueColor: AlwaysStoppedAnimation<Color>(barColor),
            minHeight: 6,
          ),
        ),
      ],
    );
  }
}
