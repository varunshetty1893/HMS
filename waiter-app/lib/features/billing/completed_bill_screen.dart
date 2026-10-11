import 'package:flutter/material.dart';
import '../../config/theme.dart';
import '../../core/utils/currency_formatter.dart';
import '../../core/utils/date_formatter.dart';
import '../../models/bill_model.dart';

class CompletedBillScreen extends StatelessWidget {
  final BillModel bill;
  final PaymentModel payment;

  const CompletedBillScreen({
    Key? key,
    required this.bill,
    required this.payment,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: const Text('Settlement Receipt'),
        automaticallyImplyLeading: false,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // Success Card
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppTheme.cardColor,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.readyColor.withOpacity(0.5)),
              ),
              child: Column(
                children: [
                  Container(
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      color: AppTheme.readyColor.withOpacity(0.2),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.check_circle,
                      color: AppTheme.readyColor,
                      size: 40,
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'BILL PAID & SETTLED',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.readyColor,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Table ${bill.tableNumber ?? ""} is now released and AVAILABLE',
                    style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Receipt Breakdown
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.cardAltColor,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.borderColor),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Bill #${bill.billNumber}', style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
                      Text('Table ${bill.tableNumber ?? ""}', style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
                    ],
                  ),
                  const Divider(color: AppTheme.borderColor, height: 20),
                  _buildReceiptRow('Payment Method', payment.paymentMethod),
                  if (payment.referenceNumber != null)
                    _buildReceiptRow('Reference No.', payment.referenceNumber!),
                  if (payment.completedAt != null)
                    _buildReceiptRow('Settled At', DateFormatter.formatDateTime(payment.completedAt!)),
                  const Divider(color: AppTheme.borderColor, height: 20),

                  // Line Items
                  const Text('Items Billed:', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
                  const SizedBox(height: 8),
                  ...bill.lineItems.map((item) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            '${item.quantityBilled}x ${item.itemName} (${item.variantName})',
                            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                          ),
                          Text(
                            CurrencyFormatter.format(item.lineTotal),
                            style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
                          ),
                        ],
                      ),
                    );
                  }),
                  const Divider(color: AppTheme.borderColor, height: 20),

                  _buildReceiptRow('Subtotal', CurrencyFormatter.format(bill.subtotalAmount)),
                  if (bill.discountAmount > 0)
                    _buildReceiptRow('Discount', '- ${CurrencyFormatter.format(bill.discountAmount)}', valueColor: AppTheme.errorColor),
                  _buildReceiptRow('CGST (2.5%)', CurrencyFormatter.format(bill.cgstAmount)),
                  _buildReceiptRow('SGST (2.5%)', CurrencyFormatter.format(bill.sgstAmount)),
                  const Divider(color: AppTheme.borderColor, height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Total Settled',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                      ),
                      Text(
                        CurrencyFormatter.format(payment.amountPaid),
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.readyColor),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Return Button
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.table_restaurant),
                label: const Text('Return to Floor Grid', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.accentColor,
                  foregroundColor: Colors.white,
                ),
                onPressed: () {
                  Navigator.of(context).popUntil((route) => route.isFirst);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReceiptRow(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
          Text(
            value,
            style: TextStyle(
              color: valueColor ?? AppTheme.textPrimary,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
