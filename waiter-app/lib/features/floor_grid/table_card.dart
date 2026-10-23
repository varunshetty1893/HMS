import 'package:flutter/material.dart';
import '../../config/theme.dart';
import '../../models/table_model.dart';
import '../../widgets/status_badge.dart';

class TableCard extends StatelessWidget {
  final TableModel table;
  final VoidCallback onTap;

  const TableCard({
    Key? key,
    required this.table,
    required this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final hasReady = (table.readyOrdersCount ?? 0) > 0;
    final activeOrders = table.activeOrdersCount ?? 0;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          decoration: BoxDecoration(
            color: AppTheme.cardColor,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: hasReady
                  ? AppTheme.readyColor
                  : table.isOccupied
                      ? AppTheme.accentColor.withOpacity(0.5)
                      : AppTheme.borderColor,
              width: hasReady ? 2.0 : 1.0,
            ),
            boxShadow: [
              if (hasReady)
                BoxShadow(
                  color: AppTheme.readyColor.withOpacity(0.2),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppTheme.cardAltColor,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'T-${table.tableNumber}',
                        style: const TextStyle(
                          color: AppTheme.textPrimary,
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                    ),
                    StatusBadge(status: table.isBilled ? 'BILLED' : table.status),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (table.displayName != null && table.displayName!.isNotEmpty)
                      Text(
                        table.displayName!,
                        style: const TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    if (table.locationDescription != null)
                      Text(
                        table.locationDescription!,
                        style: const TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 12,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        const Icon(Icons.people_outline,
                            size: 14, color: AppTheme.textSecondary),
                        const SizedBox(width: 4),
                        Text(
                          '${table.capacity} seats',
                          style: const TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    if (table.isBilled)
                      Row(
                        children: const [
                          Icon(Icons.receipt_long,
                              size: 14, color: AppTheme.warningColor),
                          SizedBox(width: 4),
                          Text(
                            'Billed · payment pending',
                            style: TextStyle(
                              color: AppTheme.warningColor,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      )
                    else if (table.isOccupied)
                      Row(
                        children: [
                          Icon(
                            Icons.receipt_long,
                            size: 14,
                            color: activeOrders > 0
                                ? AppTheme.accentColor
                                : AppTheme.textSecondary,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '$activeOrders active',
                            style: TextStyle(
                              color: activeOrders > 0
                                  ? AppTheme.accentColor
                                  : AppTheme.textSecondary,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      )
                    else
                      const Text(
                        'Tap to seat',
                        style: TextStyle(
                          color: AppTheme.successColor,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    if (hasReady)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.readyColor.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                              color: AppTheme.readyColor.withOpacity(0.5)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.dinner_dining,
                                size: 12, color: AppTheme.readyColor),
                            const SizedBox(width: 4),
                            Text(
                              '${table.readyOrdersCount} READY',
                              style: const TextStyle(
                                color: AppTheme.readyColor,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
