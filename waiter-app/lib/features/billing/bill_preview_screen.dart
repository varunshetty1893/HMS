import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../core/utils/currency_formatter.dart';
import '../../models/bill_model.dart';
import 'billing_controller.dart';
import 'payment_recording_screen.dart';

class BillPreviewScreen extends ConsumerStatefulWidget {
  final int tableNumber;
  final String? tableDisplayName;

  const BillPreviewScreen({
    Key? key,
    required this.tableNumber,
    this.tableDisplayName,
  }) : super(key: key);

  @override
  ConsumerState<BillPreviewScreen> createState() => _BillPreviewScreenState();
}

class _BillPreviewScreenState extends ConsumerState<BillPreviewScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(billingControllerProvider.notifier).loadTableBill(widget.tableNumber);
    });
  }

  void _showGenerateConfirmDialog(BuildContext context, TableBillModel tableBill) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.cardColor,
        title: Text(
          'Generate Final Bill — Table ${widget.tableNumber}',
          style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.bold),
        ),
        content: Text(
          'Total: ${CurrencyFormatter.format(tableBill.previewGrandTotal ?? 0.0)}\n\n'
          'Once generated, the table moves to Bill Pending and customer ordering will be locked. Confirm?',
          style: const TextStyle(color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel', style: TextStyle(color: AppTheme.textMuted)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.accentColor,
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              Navigator.of(ctx).pop();
              final bill = await ref.read(billingControllerProvider.notifier).generateBill(
                    tableNumber: widget.tableNumber,
                  );
              if (bill != null && mounted) {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(
                    builder: (_) => PaymentRecordingScreen(bill: bill),
                  ),
                );
              }
            },
            child: const Text('Confirm & Generate'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(billingControllerProvider);
    final tableBill = state.tableBill;
    final bill = state.bill;

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: Text('Bill — Table ${widget.tableNumber}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () =>
                ref.read(billingControllerProvider.notifier).loadTableBill(widget.tableNumber),
          ),
        ],
      ),
      body: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : state.error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error_outline, size: 48, color: AppTheme.errorColor),
                        const SizedBox(height: 12),
                        Text(
                          state.error!,
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: AppTheme.errorColor, fontSize: 16),
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: () => ref
                              .read(billingControllerProvider.notifier)
                              .loadTableBill(widget.tableNumber),
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : tableBill == null
                  ? const Center(child: Text('No billing information available'))
                  : Column(
                      children: [
                        // Status & Warnings Header
                        if (tableBill.hasUnacceptedPlacedOrders)
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                            color: Colors.red.withOpacity(0.15),
                            child: const Row(
                              children: [
                                Icon(Icons.warning_amber_rounded, color: Colors.orangeAccent),
                                SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    'Unaccepted PLACED orders exist. Kitchen must accept/reject first.',
                                    style: TextStyle(color: Colors.orangeAccent, fontSize: 13),
                                  ),
                                ),
                              ],
                            ),
                          )
                        else if (tableBill.hasUnservedOrders)
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                            color: Colors.amber.withOpacity(0.15),
                            child: const Row(
                              children: [
                                Icon(Icons.info_outline, color: Colors.amber),
                                SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    'Active unserved orders remain. Mark all items SERVED before bill generation.',
                                    style: TextStyle(color: Colors.amber, fontSize: 13),
                                  ),
                                ),
                              ],
                            ),
                          ),

                        // Itemized Order Lines List
                        Expanded(
                          child: ListView(
                            padding: const EdgeInsets.all(16),
                            children: [
                              _buildHeaderCard(tableBill, bill),
                              const SizedBox(height: 16),
                              _buildLineItemsSection(tableBill, bill),
                              const SizedBox(height: 16),
                              _buildFinancialSummaryCard(tableBill, bill),
                            ],
                          ),
                        ),

                        // Bottom Action Bar
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: const BoxDecoration(
                            color: AppTheme.surfaceColor,
                            border: Border(top: BorderSide(color: AppTheme.borderColor)),
                          ),
                          child: bill != null
                              ? SizedBox(
                                  width: double.infinity,
                                  height: 50,
                                  child: ElevatedButton.icon(
                                    icon: const Icon(Icons.payment),
                                    label: Text(
                                      'Proceed to Record Payment (${CurrencyFormatter.format(bill.grandTotal)})',
                                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                                    ),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: AppTheme.readyColor,
                                      foregroundColor: Colors.white,
                                    ),
                                    onPressed: () {
                                      Navigator.of(context).push(
                                        MaterialPageRoute(
                                          builder: (_) => PaymentRecordingScreen(bill: bill),
                                        ),
                                      );
                                    },
                                  ),
                                )
                              : SizedBox(
                                  width: double.infinity,
                                  height: 50,
                                  child: ElevatedButton.icon(
                                    icon: const Icon(Icons.receipt_long),
                                    label: const Text(
                                      'Generate Final Bill',
                                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                                    ),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: tableBill.canGenerateBill
                                          ? AppTheme.accentColor
                                          : Colors.grey.shade700,
                                      foregroundColor: Colors.white,
                                    ),
                                    onPressed: tableBill.canGenerateBill && !state.isSubmitting
                                        ? () => _showGenerateConfirmDialog(context, tableBill)
                                        : null,
                                  ),
                                ),
                        ),
                      ],
                    ),
    );
  }

  Widget _buildHeaderCard(TableBillModel tableBill, BillModel? bill) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderColor),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Table ${tableBill.tableNumber}',
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              if (tableBill.tableDisplayName != null)
                Text(
                  tableBill.tableDisplayName!,
                  style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                ),
              const SizedBox(height: 4),
              Text(
                bill != null ? 'Bill #${bill.billNumber}' : 'Session: ${tableBill.sessionCode}',
                style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
              ),
            ],
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: bill != null ? AppTheme.readyColor.withOpacity(0.2) : Colors.orange.withOpacity(0.2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              bill != null ? bill.status : 'PREVIEW',
              style: TextStyle(
                color: bill != null ? AppTheme.readyColor : Colors.orangeAccent,
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLineItemsSection(TableBillModel tableBill, BillModel? bill) {
    final items = bill != null ? bill.lineItems : tableBill.previewLineItems;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Itemized Line Items',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
          ),
          const Divider(color: AppTheme.borderColor),
          if (items.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 12),
              child: Text('No active billable items found.', style: TextStyle(color: AppTheme.textMuted)),
            )
          else
            ...items.map((item) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${item.quantityBilled}x ${item.itemName}',
                            style: const TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          Text(
                            '${item.itemCode} • ${item.variantName} @ ${CurrencyFormatter.format(item.unitPriceSnapshot)}',
                            style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                    Text(
                      CurrencyFormatter.format(item.lineTotal),
                      style: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildFinancialSummaryCard(TableBillModel tableBill, BillModel? bill) {
    final subtotal = bill != null ? bill.subtotalAmount : (tableBill.previewSubtotal ?? 0.0);
    final discount = bill?.discountAmount ?? 0.0;
    final taxable = bill != null ? bill.taxableAmount : (tableBill.previewTaxable ?? subtotal);
    final cgst = bill != null ? bill.cgstAmount : (tableBill.previewCgst ?? 0.0);
    final sgst = bill != null ? bill.sgstAmount : (tableBill.previewSgst ?? 0.0);
    final grandTotal = bill != null ? bill.grandTotal : (tableBill.previewGrandTotal ?? 0.0);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardAltColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderColor),
      ),
      child: Column(
        children: [
          _buildSummaryRow('Item Subtotal', CurrencyFormatter.format(subtotal)),
          if (discount > 0)
            _buildSummaryRow(
              'Discount',
              '- ${CurrencyFormatter.format(discount)}',
              valueColor: AppTheme.errorColor,
            ),
          _buildSummaryRow('Taxable Amount', CurrencyFormatter.format(taxable)),
          _buildSummaryRow('CGST (2.5%)', CurrencyFormatter.format(cgst)),
          _buildSummaryRow('SGST (2.5%)', CurrencyFormatter.format(sgst)),
          const Divider(color: AppTheme.borderColor, height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Grand Total',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              Text(
                CurrencyFormatter.format(grandTotal),
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.accentColor,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryRow(String label, String value, {Color? valueColor}) {
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
