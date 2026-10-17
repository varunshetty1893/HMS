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
      ref
          .read(billingControllerProvider.notifier)
          .loadTableBill(widget.tableNumber);
    });
  }

  void _showPriceAdjustDialog(BillItemModel item) {
    final state = ref.read(billingControllerProvider);
    final currentOverride = state.priceOverrides[item.id];
    final currentReason = state.priceOverrideReasons[item.id] ?? '';
    final initialPrice = currentOverride ?? item.unitPriceSnapshot;

    final priceController =
        TextEditingController(text: initialPrice.toStringAsFixed(2));
    final reasonController = TextEditingController(
        text: currentReason.isNotEmpty ? currentReason : 'Price adjusted at billing');
    final formKey = GlobalKey<FormState>();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.cardColor,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const Icon(Icons.price_change_outlined,
                color: AppTheme.accentColor, size: 24),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Adjust Price — ${item.itemName}',
                style: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
        content: Form(
          key: formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceColor,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.borderColor),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Original Unit Price:',
                        style: TextStyle(
                            color: AppTheme.textSecondary, fontSize: 13),
                      ),
                      Text(
                        CurrencyFormatter.format(item.unitPriceSnapshot),
                        style: const TextStyle(
                          color: AppTheme.textPrimary,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: priceController,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  style: const TextStyle(color: AppTheme.textPrimary),
                  decoration: const InputDecoration(
                    labelText: 'New Unit Price (₹)',
                    labelStyle: TextStyle(color: AppTheme.textSecondary),
                    prefixIcon: Icon(Icons.currency_rupee,
                        color: AppTheme.accentColor, size: 18),
                    border: OutlineInputBorder(),
                    enabledBorder: OutlineInputBorder(
                      borderSide: BorderSide(color: AppTheme.borderColor),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderSide: BorderSide(color: AppTheme.accentColor),
                    ),
                  ),
                  validator: (val) {
                    if (val == null || val.trim().isEmpty) {
                      return 'Enter new price';
                    }
                    final num = double.tryParse(val.trim());
                    if (num == null || num < 0) {
                      return 'Enter a valid non-negative price';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: reasonController,
                  style: const TextStyle(color: AppTheme.textPrimary),
                  decoration: const InputDecoration(
                    labelText: 'Reason for Adjustment',
                    labelStyle: TextStyle(color: AppTheme.textSecondary),
                    hintText: 'e.g. VIP discount, Special deal, Customer courtesy',
                    hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                    prefixIcon: Icon(Icons.edit_note,
                        color: AppTheme.textSecondary, size: 20),
                    border: OutlineInputBorder(),
                    enabledBorder: OutlineInputBorder(
                      borderSide: BorderSide(color: AppTheme.borderColor),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderSide: BorderSide(color: AppTheme.accentColor),
                    ),
                  ),
                  validator: (val) {
                    if (val == null || val.trim().isEmpty) {
                      return 'Reason is required';
                    }
                    return null;
                  },
                ),
              ],
            ),
          ),
        ),
        actions: [
          if (currentOverride != null && item.id != null)
            TextButton(
              onPressed: () {
                ref
                    .read(billingControllerProvider.notifier)
                    .removePriceOverride(item.id!);
                Navigator.of(ctx).pop();
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Reset ${item.itemName} to original price'),
                    backgroundColor: AppTheme.surfaceColor,
                  ),
                );
              },
              child: const Text('Reset',
                  style: TextStyle(color: AppTheme.errorColor)),
            ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel',
                style: TextStyle(color: AppTheme.textMuted)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.accentColor,
              foregroundColor: Colors.white,
            ),
            onPressed: () {
              if (formKey.currentState?.validate() ?? false) {
                final newPrice = double.parse(priceController.text.trim());
                final reason = reasonController.text.trim();
                if (item.id != null) {
                  ref
                      .read(billingControllerProvider.notifier)
                      .setPriceOverride(item.id!, newPrice, reason);
                  Navigator.of(ctx).pop();
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                          'Updated ${item.itemName} price to ${CurrencyFormatter.format(newPrice)}'),
                      backgroundColor: AppTheme.readyColor,
                    ),
                  );
                }
              }
            },
            child: const Text('Apply Price'),
          ),
        ],
      ),
    );
  }

  void _showDiscountDialog({
    required double currentSubtotal,
    required bool isIssuedBill,
    String? billId,
  }) {
    final state = ref.read(billingControllerProvider);
    final initialDiscount = state.discountAmount;
    final initialReason = state.discountReason ?? '';

    bool isPercent = false;
    final amountController = TextEditingController(
      text: initialDiscount > 0 ? initialDiscount.toStringAsFixed(2) : '',
    );
    final reasonController = TextEditingController(
      text: initialReason.isNotEmpty ? initialReason : 'Courtesy discount',
    );
    final formKey = GlobalKey<FormState>();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) {
          double calculatedDiscount = 0.0;
          final inputVal = double.tryParse(amountController.text.trim()) ?? 0.0;
          if (isPercent) {
            calculatedDiscount = (currentSubtotal * inputVal / 100.0);
          } else {
            calculatedDiscount = inputVal;
          }
          if (calculatedDiscount > currentSubtotal) {
            calculatedDiscount = currentSubtotal;
          }

          return AlertDialog(
            backgroundColor: AppTheme.cardColor,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: Row(
              children: [
                const Icon(Icons.local_offer_outlined,
                    color: AppTheme.accentColor, size: 24),
                const SizedBox(width: 8),
                Text(
                  isIssuedBill ? 'Apply Bill Discount' : 'Add Bill Discount',
                  style: const TextStyle(
                    color: AppTheme.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            content: Form(
              key: formKey,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceColor,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppTheme.borderColor),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Subtotal:',
                              style: TextStyle(
                                  color: AppTheme.textSecondary, fontSize: 13)),
                          Text(
                            CurrencyFormatter.format(currentSubtotal),
                            style: const TextStyle(
                              color: AppTheme.textPrimary,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    // Toggle Flat Amount vs Percentage
                    Row(
                      children: [
                        Expanded(
                          child: InkWell(
                            onTap: () {
                              setDialogState(() {
                                isPercent = false;
                              });
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 8),
                              decoration: BoxDecoration(
                                color: !isPercent
                                    ? AppTheme.accentColor
                                    : AppTheme.surfaceColor,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                  color: !isPercent
                                      ? AppTheme.accentColor
                                      : AppTheme.borderColor,
                                ),
                              ),
                              child: Center(
                                child: Text(
                                  'Flat Amount (₹)',
                                  style: TextStyle(
                                    color: !isPercent
                                        ? Colors.white
                                        : AppTheme.textSecondary,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: InkWell(
                            onTap: () {
                              setDialogState(() {
                                isPercent = true;
                              });
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 8),
                              decoration: BoxDecoration(
                                color: isPercent
                                    ? AppTheme.accentColor
                                    : AppTheme.surfaceColor,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                  color: isPercent
                                      ? AppTheme.accentColor
                                      : AppTheme.borderColor,
                                ),
                              ),
                              child: Center(
                                child: Text(
                                  'Percentage (%)',
                                  style: TextStyle(
                                    color: isPercent
                                        ? Colors.white
                                        : AppTheme.textSecondary,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    TextFormField(
                      controller: amountController,
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                      style: const TextStyle(color: AppTheme.textPrimary),
                      onChanged: (_) => setDialogState(() {}),
                      decoration: InputDecoration(
                        labelText: isPercent
                            ? 'Discount Percentage (%)'
                            : 'Discount Amount (₹)',
                        labelStyle:
                            const TextStyle(color: AppTheme.textSecondary),
                        prefixIcon: Icon(
                          isPercent
                              ? Icons.percent
                              : Icons.currency_rupee,
                          color: AppTheme.accentColor,
                          size: 18,
                        ),
                        border: const OutlineInputBorder(),
                        enabledBorder: const OutlineInputBorder(
                          borderSide: BorderSide(color: AppTheme.borderColor),
                        ),
                        focusedBorder: const OutlineInputBorder(
                          borderSide: BorderSide(color: AppTheme.accentColor),
                        ),
                      ),
                      validator: (val) {
                        if (val == null || val.trim().isEmpty) {
                          return 'Enter discount value';
                        }
                        final num = double.tryParse(val.trim());
                        if (num == null || num <= 0) {
                          return 'Enter a positive discount value';
                        }
                        if (isPercent && num > 100) {
                          return 'Cannot exceed 100%';
                        }
                        if (!isPercent && num > currentSubtotal) {
                          return 'Cannot exceed subtotal';
                        }
                        return null;
                      },
                    ),
                    if (isPercent && calculatedDiscount > 0)
                      Padding(
                        padding: const EdgeInsets.only(top: 6, left: 4),
                        child: Text(
                          'Calculated Discount: ${CurrencyFormatter.format(calculatedDiscount)}',
                          style: const TextStyle(
                              color: AppTheme.readyColor,
                              fontSize: 12,
                              fontWeight: FontWeight.bold),
                        ),
                      ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: reasonController,
                      style: const TextStyle(color: AppTheme.textPrimary),
                      decoration: const InputDecoration(
                        labelText: 'Discount Reason',
                        labelStyle: TextStyle(color: AppTheme.textSecondary),
                        hintText: 'e.g. Regular customer, Management courtesy',
                        hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                        prefixIcon: Icon(Icons.edit_note,
                            color: AppTheme.textSecondary, size: 20),
                        border: OutlineInputBorder(),
                        enabledBorder: OutlineInputBorder(
                          borderSide: BorderSide(color: AppTheme.borderColor),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderSide: BorderSide(color: AppTheme.accentColor),
                        ),
                      ),
                      validator: (val) {
                        if (val == null || val.trim().isEmpty) {
                          return 'Discount reason is required';
                        }
                        return null;
                      },
                    ),
                  ],
                ),
              ),
            ),
            actions: [
              if (initialDiscount > 0)
                TextButton(
                  onPressed: () async {
                    if (isIssuedBill && billId != null) {
                      await ref
                          .read(billingControllerProvider.notifier)
                          .applyDiscountToIssuedBill(
                            billId: billId,
                            discountAmount: 0.0,
                            reason: 'Discount removed',
                          );
                    } else {
                      ref
                          .read(billingControllerProvider.notifier)
                          .removeDiscount();
                    }
                    Navigator.of(ctx).pop();
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Discount removed'),
                        backgroundColor: AppTheme.surfaceColor,
                      ),
                    );
                  },
                  child: const Text('Remove',
                      style: TextStyle(color: AppTheme.errorColor)),
                ),
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('Cancel',
                    style: TextStyle(color: AppTheme.textMuted)),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.accentColor,
                  foregroundColor: Colors.white,
                ),
                onPressed: () async {
                  if (formKey.currentState?.validate() ?? false) {
                    final reason = reasonController.text.trim();
                    final finalDiscount = calculatedDiscount;

                    Navigator.of(ctx).pop();

                    if (isIssuedBill && billId != null) {
                      final updated = await ref
                          .read(billingControllerProvider.notifier)
                          .applyDiscountToIssuedBill(
                            billId: billId,
                            discountAmount: finalDiscount,
                            reason: reason,
                          );
                      if (updated != null && mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                                'Applied discount of ${CurrencyFormatter.format(finalDiscount)}'),
                            backgroundColor: AppTheme.readyColor,
                          ),
                        );
                      }
                    } else {
                      ref
                          .read(billingControllerProvider.notifier)
                          .setDiscount(finalDiscount, reason);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                              'Discount of ${CurrencyFormatter.format(finalDiscount)} applied to preview'),
                          backgroundColor: AppTheme.readyColor,
                        ),
                      );
                    }
                  }
                },
                child: const Text('Apply Discount'),
              ),
            ],
          );
        },
      ),
    );
  }

  void _showGenerateConfirmDialog({
    required BuildContext context,
    required double grandTotal,
    required double discount,
    required int overridesCount,
  }) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.cardColor,
        title: Text(
          'Generate Final Bill — Table ${widget.tableNumber}',
          style: const TextStyle(
              color: AppTheme.textPrimary, fontWeight: FontWeight.bold),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Grand Total: ${CurrencyFormatter.format(grandTotal)}',
              style: const TextStyle(
                color: AppTheme.accentColor,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            if (overridesCount > 0)
              Text(
                '• $overridesCount price adjustment(s) included.',
                style: const TextStyle(color: AppTheme.readyColor, fontSize: 13),
              ),
            if (discount > 0)
              Text(
                '• Discount of ${CurrencyFormatter.format(discount)} applied.',
                style: const TextStyle(color: AppTheme.readyColor, fontSize: 13),
              ),
            const SizedBox(height: 12),
            const Text(
              'Once generated, the table moves to Bill Pending and customer ordering will be locked. Confirm?',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel',
                style: TextStyle(color: AppTheme.textMuted)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.accentColor,
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              Navigator.of(ctx).pop();
              final bill = await ref
                  .read(billingControllerProvider.notifier)
                  .generateBill(
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
            tooltip: 'Refresh Bill',
            onPressed: () => ref
                .read(billingControllerProvider.notifier)
                .loadTableBill(widget.tableNumber),
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
                        const Icon(Icons.error_outline,
                            size: 48, color: AppTheme.errorColor),
                        const SizedBox(height: 12),
                        Text(
                          state.error!,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                              color: AppTheme.errorColor, fontSize: 16),
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
                  ? const Center(
                      child: Text('No billing information available'))
                  : _buildBillContent(context, state, tableBill, bill),
    );
  }

  Widget _buildBillContent(
    BuildContext context,
    BillingState state,
    TableBillModel tableBill,
    BillModel? bill,
  ) {
    // Calculate live financial figures
    double liveSubtotal = 0.0;
    if (bill != null) {
      liveSubtotal = bill.subtotalAmount;
    } else {
      for (final item in tableBill.previewLineItems) {
        final effectivePrice =
            state.priceOverrides[item.id] ?? item.unitPriceSnapshot;
        liveSubtotal += effectivePrice * item.quantityBilled;
      }
    }

    final liveDiscount =
        bill != null ? bill.discountAmount : state.discountAmount;
    final liveDiscountReason =
        bill != null ? bill.discountReason : state.discountReason;

    final liveTaxable =
        (liveSubtotal > liveDiscount ? liveSubtotal - liveDiscount : 0.0);
    final liveCgst = (liveTaxable * 0.025);
    final liveSgst = (liveTaxable * 0.025);
    final liveGrandTotal = (liveTaxable + liveCgst + liveSgst);

    return Column(
      children: [
        // Status & Warnings Header
        if (tableBill.hasUnacceptedPlacedOrders)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            color: Colors.red.withOpacity(0.15),
            child: const Row(
              children: [
                Icon(Icons.warning_amber_rounded, color: Color(0xFFC2410C)),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Unaccepted PLACED orders exist. Kitchen must accept/reject first.',
                    style: TextStyle(color: Color(0xFFC2410C), fontSize: 13),
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
                Icon(Icons.info_outline, color: Color(0xFFB45309)),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Active unserved orders remain. Mark all items SERVED before bill generation.',
                    style: TextStyle(color: Color(0xFFB45309), fontSize: 13),
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
              _buildLineItemsSection(tableBill, bill, state),
              const SizedBox(height: 16),
              _buildFinancialSummaryCard(
                subtotal: liveSubtotal,
                discount: liveDiscount,
                discountReason: liveDiscountReason,
                taxable: liveTaxable,
                cgst: liveCgst,
                sgst: liveSgst,
                grandTotal: liveGrandTotal,
                isIssuedBill: bill != null,
                billId: bill?.id,
              ),
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
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold),
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
                    label: Text(
                      'Generate Final Bill (${CurrencyFormatter.format(liveGrandTotal)})',
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: tableBill.canGenerateBill
                          ? AppTheme.accentColor
                          : Colors.grey.shade700,
                      foregroundColor: Colors.white,
                    ),
                    onPressed: tableBill.canGenerateBill && !state.isSubmitting
                        ? () => _showGenerateConfirmDialog(
                              context: context,
                              grandTotal: liveGrandTotal,
                              discount: liveDiscount,
                              overridesCount: state.priceOverrides.length,
                            )
                        : null,
                  ),
                ),
        ),
      ],
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
                  style: const TextStyle(
                      color: AppTheme.textSecondary, fontSize: 13),
                ),
              const SizedBox(height: 4),
              Text(
                bill != null
                    ? 'Bill #${bill.billNumber}'
                    : 'Session: ${tableBill.sessionCode}',
                style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
              ),
            ],
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: bill != null
                  ? AppTheme.readyColor.withOpacity(0.2)
                  : Colors.orange.withOpacity(0.2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              bill != null ? bill.status : 'PREVIEW',
              style: TextStyle(
                color: bill != null ? AppTheme.readyColor : const Color(0xFFC2410C),
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLineItemsSection(
    TableBillModel tableBill,
    BillModel? bill,
    BillingState state,
  ) {
    final items = bill != null ? bill.lineItems : tableBill.previewLineItems;
    final isPreview = bill == null;

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
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Itemized Line Items',
                style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.textPrimary),
              ),
              if (isPreview && items.isNotEmpty)
                const Text(
                  'Tap item to change price',
                  style: TextStyle(
                      fontSize: 11,
                      color: AppTheme.accentColor,
                      fontStyle: FontStyle.italic),
                ),
            ],
          ),
          const Divider(color: AppTheme.borderColor),
          if (items.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 12),
              child: Text('No active billable items found.',
                  style: TextStyle(color: AppTheme.textMuted)),
            )
          else
            ...items.map((item) {
              final overridePrice =
                  isPreview ? state.priceOverrides[item.id] : null;
              final overrideReason =
                  isPreview ? state.priceOverrideReasons[item.id] : null;

              final displayUnitPrice = overridePrice ?? item.unitPriceSnapshot;
              final displayLineTotal =
                  overridePrice != null
                      ? (overridePrice * item.quantityBilled)
                      : item.lineTotal;

              return InkWell(
                onTap: isPreview ? () => _showPriceAdjustDialog(item) : null,
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    '${item.quantityBilled}x ${item.itemName}',
                                    style: const TextStyle(
                                      color: AppTheme.textPrimary,
                                      fontSize: 14,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                                if (isPreview)
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: overridePrice != null
                                          ? AppTheme.accentColor.withOpacity(0.15)
                                          : AppTheme.surfaceColor,
                                      borderRadius: BorderRadius.circular(4),
                                      border: Border.all(
                                        color: overridePrice != null
                                            ? AppTheme.accentColor
                                            : AppTheme.borderColor,
                                      ),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(
                                          Icons.edit,
                                          size: 11,
                                          color: overridePrice != null
                                              ? AppTheme.accentColor
                                              : AppTheme.textMuted,
                                        ),
                                        const SizedBox(width: 3),
                                        Text(
                                          overridePrice != null
                                              ? 'Edited'
                                              : 'Edit Price',
                                          style: TextStyle(
                                            fontSize: 10,
                                            fontWeight: FontWeight.bold,
                                            color: overridePrice != null
                                                ? AppTheme.accentColor
                                                : AppTheme.textMuted,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                              ],
                            ),
                            const SizedBox(height: 3),
                            Row(
                              children: [
                                Text(
                                  '${item.itemCode} • ${item.variantName} @ ',
                                  style: const TextStyle(
                                      color: AppTheme.textMuted, fontSize: 12),
                                ),
                                if (overridePrice != null) ...[
                                  Text(
                                    CurrencyFormatter.format(
                                        item.unitPriceSnapshot),
                                    style: const TextStyle(
                                      color: AppTheme.textMuted,
                                      fontSize: 11,
                                      decoration: TextDecoration.lineThrough,
                                    ),
                                  ),
                                  const SizedBox(width: 4),
                                ],
                                Text(
                                  CurrencyFormatter.format(displayUnitPrice),
                                  style: TextStyle(
                                    color: overridePrice != null
                                        ? AppTheme.accentColor
                                        : AppTheme.textSecondary,
                                    fontSize: 12,
                                    fontWeight: overridePrice != null
                                        ? FontWeight.bold
                                        : FontWeight.normal,
                                  ),
                                ),
                              ],
                            ),
                            if (overrideReason != null &&
                                overrideReason.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(top: 2),
                                child: Text(
                                  'Reason: $overrideReason',
                                  style: const TextStyle(
                                    color: AppTheme.accentColor,
                                    fontSize: 11,
                                    fontStyle: FontStyle.italic,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        CurrencyFormatter.format(displayLineTotal),
                        style: TextStyle(
                          color: overridePrice != null
                              ? AppTheme.accentColor
                              : AppTheme.textPrimary,
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildFinancialSummaryCard({
    required double subtotal,
    required double discount,
    required String? discountReason,
    required double taxable,
    required double cgst,
    required double sgst,
    required double grandTotal,
    required bool isIssuedBill,
    String? billId,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardAltColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderColor),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Financial Summary',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              // Add / Edit Discount button
              InkWell(
                onTap: () => _showDiscountDialog(
                  currentSubtotal: subtotal,
                  isIssuedBill: isIssuedBill,
                  billId: billId,
                ),
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: discount > 0
                        ? AppTheme.readyColor.withOpacity(0.15)
                        : AppTheme.accentColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: discount > 0
                          ? AppTheme.readyColor
                          : AppTheme.accentColor,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.local_offer,
                        size: 13,
                        color: discount > 0
                            ? AppTheme.readyColor
                            : AppTheme.accentColor,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        discount > 0 ? 'Edit Discount' : '+ Add Discount',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: discount > 0
                              ? AppTheme.readyColor
                              : AppTheme.accentColor,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const Divider(color: AppTheme.borderColor, height: 16),
          _buildSummaryRow('Item Subtotal', CurrencyFormatter.format(subtotal)),
          if (discount > 0)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Discount',
                          style: TextStyle(
                              color: AppTheme.readyColor,
                              fontSize: 13,
                              fontWeight: FontWeight.w600)),
                      if (discountReason != null && discountReason.isNotEmpty)
                        Text(
                          '($discountReason)',
                          style: const TextStyle(
                              color: AppTheme.textMuted, fontSize: 11),
                        ),
                    ],
                  ),
                  Text(
                    '- ${CurrencyFormatter.format(discount)}',
                    style: const TextStyle(
                      color: AppTheme.readyColor,
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
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
          Text(label,
              style:
                  const TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
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
