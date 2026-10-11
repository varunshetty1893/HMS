import 'package:flutter/material.dart';
import '../../config/theme.dart';

class OrderCancelDialog extends StatefulWidget {
  final String orderId;
  final String orderNumber;

  const OrderCancelDialog({
    Key? key,
    required this.orderId,
    required this.orderNumber,
  }) : super(key: key);

  static Future<String?> show(
    BuildContext context, {
    required String orderId,
    required String orderNumber,
  }) {
    return showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (_) => OrderCancelDialog(
        orderId: orderId,
        orderNumber: orderNumber,
      ),
    );
  }

  @override
  State<OrderCancelDialog> createState() => _OrderCancelDialogState();
}

class _OrderCancelDialogState extends State<OrderCancelDialog> {
  final _reasonController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppTheme.cardColor,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: Row(
        children: [
          const Icon(Icons.warning_amber_rounded,
              color: AppTheme.errorColor, size: 28),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Cancel Order #${widget.orderNumber}',
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
            const Text(
              'Please provide a mandatory cancellation reason for the audit trail:',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _reasonController,
              autofocus: true,
              maxLines: 3,
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14),
              decoration: InputDecoration(
                hintText: 'e.g., Customer changed mind, duplicate order...',
                hintStyle: const TextStyle(color: AppTheme.textMuted),
                filled: true,
                fillColor: AppTheme.surfaceColor,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppTheme.borderColor),
                ),
              ),
              validator: (val) {
                if (val == null || val.trim().isEmpty) {
                  return 'Reason cannot be empty';
                }
                if (val.trim().length < 5) {
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
          child: const Text('Confirm Cancel'),
        ),
      ],
    );
  }
}
