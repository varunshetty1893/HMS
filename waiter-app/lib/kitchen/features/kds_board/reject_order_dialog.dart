import '../../config/kds_theme.dart';
import 'package:flutter/material.dart';

class RejectOrderDialog extends StatefulWidget {
  final String orderNumber;
  final ValueChanged<String> onConfirm;

  const RejectOrderDialog({
    super.key,
    required this.orderNumber,
    required this.onConfirm,
  });

  @override
  State<RejectOrderDialog> createState() => _RejectOrderDialogState();
}

class _RejectOrderDialogState extends State<RejectOrderDialog> {
  final TextEditingController _customReasonController = TextEditingController();
  String _selectedReason = 'Item out of stock';

  final List<String> _presetReasons = [
    'Item out of stock',
    'Kitchen closing for the day',
    'Special ingredient unavailable',
    'Cooking equipment malfunction',
    'Custom reason',
  ];

  @override
  void dispose() {
    _customReasonController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: KdsTheme.surface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: Row(
        children: [
          const Icon(Icons.cancel_outlined, color: Colors.redAccent, size: 24),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Reject Order #${widget.orderNumber}',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: KdsTheme.textPrimary),
            ),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Select a mandatory reason to notify the table and waiter:',
              style: TextStyle(color: KdsTheme.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 12),
            ..._presetReasons.map((reason) {
              return RadioListTile<String>(
                dense: true,
                contentPadding: EdgeInsets.zero,
                activeColor: Colors.orange,
                title: Text(reason, style: const TextStyle(color: KdsTheme.textPrimary, fontSize: 14)),
                value: reason,
                groupValue: _selectedReason,
                onChanged: (val) {
                  if (val != null) setState(() => _selectedReason = val);
                },
              );
            }),
            if (_selectedReason == 'Custom reason') ...[
              const SizedBox(height: 8),
              TextField(
                controller: _customReasonController,
                style: const TextStyle(color: KdsTheme.textPrimary, fontSize: 14),
                decoration: InputDecoration(
                  hintText: 'Enter specific rejection reason...',
                  hintStyle: const TextStyle(color: KdsTheme.textMuted, fontSize: 13),
                  filled: true,
                  fillColor: KdsTheme.background,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: const BorderSide(color: KdsTheme.border),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel', style: TextStyle(color: KdsTheme.textSecondary)),
        ),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.redAccent,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
          onPressed: () {
            final reason = _selectedReason == 'Custom reason'
                ? _customReasonController.text.trim()
                : _selectedReason;
            if (reason.isEmpty) return;
            widget.onConfirm(reason);
            Navigator.of(context).pop();
          },
          child: const Text('Confirm Reject'),
        ),
      ],
    );
  }
}
