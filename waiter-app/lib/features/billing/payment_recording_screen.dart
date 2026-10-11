import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../core/utils/currency_formatter.dart';
import '../../models/bill_model.dart';
import 'billing_controller.dart';
import 'completed_bill_screen.dart';

class PaymentRecordingScreen extends ConsumerStatefulWidget {
  final BillModel bill;

  const PaymentRecordingScreen({
    Key? key,
    required this.bill,
  }) : super(key: key);

  @override
  ConsumerState<PaymentRecordingScreen> createState() => _PaymentRecordingScreenState();
}

class _PaymentRecordingScreenState extends ConsumerState<PaymentRecordingScreen> {
  String _selectedMethod = 'CASH';
  final TextEditingController _refController = TextEditingController();
  final TextEditingController _notesController = TextEditingController();
  final TextEditingController _cashTenderedController = TextEditingController();
  double _changeToReturn = 0.0;

  @override
  void dispose() {
    _refController.dispose();
    _notesController.dispose();
    _cashTenderedController.dispose();
    super.dispose();
  }

  void _onCashTenderedChanged(String val) {
    final tendered = double.tryParse(val) ?? 0.0;
    setState(() {
      _changeToReturn = tendered > widget.bill.grandTotal ? tendered - widget.bill.grandTotal : 0.0;
    });
  }

  void _confirmAndRecordPayment(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.cardColor,
        title: Text(
          'Confirm Payment — ${_selectedMethod}',
          style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.bold),
        ),
        content: Text(
          'Confirm ₹${widget.bill.grandTotal.toStringAsFixed(2)} collected via $_selectedMethod?\n\n'
          'This will mark the bill PAID, complete all orders, and free Table ${widget.bill.tableNumber ?? ""}.',
          style: const TextStyle(color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel', style: TextStyle(color: AppTheme.textMuted)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.readyColor,
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              Navigator.of(ctx).pop();
              final payment = await ref.read(billingControllerProvider.notifier).recordPayment(
                    billId: widget.bill.id,
                    paymentMethod: _selectedMethod,
                    amountPaid: widget.bill.grandTotal,
                    referenceNumber: _refController.text.trim().isNotEmpty ? _refController.text.trim() : null,
                    notes: _notesController.text.trim().isNotEmpty ? _notesController.text.trim() : null,
                  );

              if (payment != null && mounted) {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(
                    builder: (_) => CompletedBillScreen(
                      bill: widget.bill,
                      payment: payment,
                    ),
                  ),
                );
              }
            },
            child: const Text('Confirm Payment'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(billingControllerProvider);

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: Text('Record Settlement — #${widget.bill.billNumber}'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Bill Grand Total Card
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppTheme.cardColor,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.borderColor),
              ),
              child: Column(
                children: [
                  Text(
                    'Bill #${widget.bill.billNumber} • Table ${widget.bill.tableNumber ?? ""}',
                    style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    CurrencyFormatter.format(widget.bill.grandTotal),
                    style: const TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.readyColor,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Total Settlement Amount Due',
                    style: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Payment Method Selector
            const Text(
              'Select Payment Method',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(child: _buildMethodCard('CASH', Icons.payments, 'Cash')),
                const SizedBox(width: 8),
                Expanded(child: _buildMethodCard('UPI', Icons.qr_code_scanner, 'UPI')),
                const SizedBox(width: 8),
                Expanded(child: _buildMethodCard('CARD', Icons.credit_card, 'Card')),
              ],
            ),
            const SizedBox(height: 20),

            // Cash Helper
            if (_selectedMethod == 'CASH') ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.cardAltColor,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.borderColor),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Cash Change Calculator (Optional)',
                      style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _cashTenderedController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      onChanged: _onCashTenderedChanged,
                      decoration: const InputDecoration(
                        labelText: 'Cash Received From Customer (₹)',
                        hintText: 'e.g. 500 or 1000',
                        prefixIcon: Icon(Icons.currency_rupee),
                      ),
                    ),
                    if (_changeToReturn > 0) ...[
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppTheme.accentColor.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text(
                              'Return Change to Guest:',
                              style: TextStyle(color: AppTheme.accentColor, fontWeight: FontWeight.bold),
                            ),
                            Text(
                              CurrencyFormatter.format(_changeToReturn),
                              style: const TextStyle(
                                color: AppTheme.accentColor,
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ] else ...[
              // UPI/CARD Notice
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.verified_user, color: Colors.lightBlueAccent, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _selectedMethod == 'UPI'
                            ? 'Verify payment notification on UPI soundbox/terminal before submitting.'
                            : 'Ensure card swipe/tap approved successfully on POS terminal.',
                        style: const TextStyle(color: Colors.lightBlueAccent, fontSize: 12),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _refController,
                decoration: InputDecoration(
                  labelText: _selectedMethod == 'UPI' ? 'UPI UTR / Reference No. (Optional)' : 'Card Last 4 Digits / Auth Code',
                  hintText: 'e.g. 427819044123',
                  prefixIcon: const Icon(Icons.tag),
                ),
              ),
              const SizedBox(height: 16),
            ],

            TextField(
              controller: _notesController,
              decoration: const InputDecoration(
                labelText: 'Notes (Optional)',
                hintText: 'e.g. Guest requested invoice copy',
                prefixIcon: Icon(Icons.note_alt_outlined),
              ),
            ),
            const SizedBox(height: 24),

            if (state.error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Text(
                  state.error!,
                  style: const TextStyle(color: AppTheme.errorColor),
                ),
              ),

            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.check_circle, size: 22),
                label: Text(
                  state.isSubmitting
                      ? 'Recording Settlement...'
                      : 'Mark Bill Paid — ${CurrencyFormatter.format(widget.bill.grandTotal)}',
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.readyColor,
                  foregroundColor: Colors.white,
                ),
                onPressed: state.isSubmitting ? null : () => _confirmAndRecordPayment(context),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMethodCard(String method, IconData icon, String label) {
    final isSelected = _selectedMethod == method;
    return InkWell(
      onTap: () => setState(() => _selectedMethod = method),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.accentColor.withOpacity(0.15) : AppTheme.cardColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? AppTheme.accentColor : AppTheme.borderColor,
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Column(
          children: [
            Icon(
              icon,
              size: 28,
              color: isSelected ? AppTheme.accentColor : AppTheme.textSecondary,
            ),
            const SizedBox(height: 8),
            Text(
              label,
              style: TextStyle(
                color: isSelected ? AppTheme.accentColor : AppTheme.textPrimary,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
