import 'package:flutter/material.dart';
import '../../config/theme.dart';

/// Confirmation + mandatory reason for a FORCE cancellation (waiter only).
/// Returns the trimmed reason, or null if the waiter backed out.
class ForceCancelDialog extends StatefulWidget {
  final String orderNumber;
  final String status;

  const ForceCancelDialog({
    Key? key,
    required this.orderNumber,
    required this.status,
  }) : super(key: key);

  static Future<String?> show(
    BuildContext context, {
    required String orderNumber,
    required String status,
  }) {
    return showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (_) => ForceCancelDialog(orderNumber: orderNumber, status: status),
    );
  }

  @override
  State<ForceCancelDialog> createState() => _ForceCancelDialogState();
}

class _ForceCancelDialogState extends State<ForceCancelDialog> {
  final _reasonController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  String get _kitchenNote => widget.status == 'READY'
      ? 'The food is already READY. The kitchen will be told to discard it.'
      : 'The kitchen is already cooking this. They will be alerted to STOP cooking.';

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppTheme.cardColor,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: Row(
        children: [
          const Icon(Icons.local_fire_department,
              color: AppTheme.errorColor, size: 28),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Force Cancel #${widget.orderNumber}',
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppTheme.errorColor.withOpacity(0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                '$_kitchenNote The whole order is removed from the bill. This is logged against your name.',
                style: const TextStyle(
                    color: AppTheme.errorColor, fontSize: 12.5),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _reasonController,
              autofocus: true,
              maxLines: 3,
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14),
              decoration: InputDecoration(
                labelText: 'Reason (required)',
                hintText: 'e.g., Guest left the table, wrong order taken...',
                filled: true,
                fillColor: AppTheme.surfaceColor,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppTheme.borderColor),
                ),
              ),
              validator: (val) {
                if (val == null || val.trim().length < 5) {
                  return 'Reason must be at least 5 characters';
                }
                return null;
              },
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(null),
          child: const Text('Back',
              style: TextStyle(color: AppTheme.textSecondary)),
        ),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.errorColor,
            foregroundColor: Colors.white,
          ),
          onPressed: () {
            if (_formKey.currentState!.validate()) {
              Navigator.of(context).pop(_reasonController.text.trim());
            }
          },
          child: const Text('Force Cancel'),
        ),
      ],
    );
  }
}
