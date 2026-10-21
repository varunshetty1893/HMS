import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
    Future.microtask(() => ref
        .read(billingControllerProvider.notifier)
        .loadTableBill(widget.tableNumber));
  }

  // ────────────────────────────────────────────────────────────────────────────
  // Dialogs
  // ────────────────────────────────────────────────────────────────────────────

  /// Full edit dialog: waiter sets quantity AND unit price for one line item.
  void _showEditItemDialog(BillItemModel item, BillingState st) {
    final existing = st.itemOverrides[item.id];
    final qtyCtrl = TextEditingController(
        text: (existing?.quantity ?? item.quantityBilled).toString());
    final priceCtrl = TextEditingController(
        text: (existing?.unitPrice ?? item.unitPriceSnapshot)
            .toStringAsFixed(2));
    final reasonCtrl =
        TextEditingController(text: existing?.reason ?? 'Price adjusted at billing');
    final formKey = GlobalKey<FormState>();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setDS) {
        double livePrice =
            double.tryParse(priceCtrl.text) ?? item.unitPriceSnapshot;
        int liveQty = int.tryParse(qtyCtrl.text) ?? item.quantityBilled;
        double liveTotal = livePrice * liveQty;

        return AlertDialog(
          backgroundColor: WaiterTheme.surface,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Row(
            children: [
              const Icon(Icons.edit_note, color: WaiterTheme.primary),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Edit: ${item.itemName}',
                  style: const TextStyle(
                      color: WaiterTheme.textPrimary,
                      fontSize: 16,
                      fontWeight: FontWeight.bold),
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
                  // Original info row
                  _infoChip('Original',
                      '${item.quantityBilled} × ${CurrencyFormatter.format(item.unitPriceSnapshot)}  =  ${CurrencyFormatter.format(item.unitPriceSnapshot * item.quantityBilled)}'),
                  const SizedBox(height: 16),

                  // ── Quantity ──────────────────────────────────
                  const Text('Quantity to Bill',
                      style: TextStyle(
                          color: WaiterTheme.textSecondary,
                          fontSize: 12,
                          fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      _qtyButton(Icons.remove, () {
                        final v = (int.tryParse(qtyCtrl.text) ?? 1) - 1;
                        if (v >= 0) {
                          qtyCtrl.text = v.toString();
                          setDS(() {});
                        }
                      }),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextFormField(
                          controller: qtyCtrl,
                          keyboardType: TextInputType.number,
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly
                          ],
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                              color: WaiterTheme.textPrimary,
                              fontSize: 20,
                              fontWeight: FontWeight.bold),
                          decoration: _inputDec(null),
                          onChanged: (_) => setDS(() {}),
                          validator: (v) {
                            final n = int.tryParse(v ?? '');
                            if (n == null || n < 0) return 'Enter qty ≥ 0';
                            return null;
                          },
                        ),
                      ),
                      const SizedBox(width: 8),
                      _qtyButton(Icons.add, () {
                        final v = (int.tryParse(qtyCtrl.text) ?? 0) + 1;
                        qtyCtrl.text = v.toString();
                        setDS(() {});
                      }),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // ── Unit Price ────────────────────────────────
                  const Text('Unit Price (₹)',
                      style: TextStyle(
                          color: WaiterTheme.textSecondary,
                          fontSize: 12,
                          fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  TextFormField(
                    controller: priceCtrl,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    style: const TextStyle(
                        color: WaiterTheme.textPrimary, fontSize: 16),
                    decoration: _inputDec('₹'),
                    onChanged: (_) => setDS(() {}),
                    validator: (v) {
                      final n = double.tryParse(v ?? '');
                      if (n == null || n < 0) return 'Enter valid price ≥ 0';
                      return null;
                    },
                  ),
                  const SizedBox(height: 12),

                  // ── Live line total ───────────────────────────
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: WaiterTheme.primary.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                          color: WaiterTheme.primary.withOpacity(0.4)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('New Line Total:',
                            style: TextStyle(
                                color: WaiterTheme.textSecondary, fontSize: 13)),
                        Text(
                          CurrencyFormatter.format(liveTotal),
                          style: const TextStyle(
                            color: WaiterTheme.primary,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),

                  // ── Reason ────────────────────────────────────
                  const Text('Reason (required)',
                      style: TextStyle(
                          color: WaiterTheme.textSecondary,
                          fontSize: 12,
                          fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  TextFormField(
                    controller: reasonCtrl,
                    style: const TextStyle(
                        color: WaiterTheme.textPrimary, fontSize: 14),
                    decoration: _inputDec(null).copyWith(
                      hintText:
                          'e.g. Customer request, VIP, special deal …',
                      hintStyle: const TextStyle(
                          color: WaiterTheme.textMuted, fontSize: 12),
                    ),
                    validator: (v) {
                      if (v == null || v.trim().length < 3) {
                        return 'Reason must be at least 3 characters';
                      }
                      return null;
                    },
                  ),
                ],
              ),
            ),
          ),
          actions: [
            if (existing != null && item.id != null)
              TextButton(
                onPressed: () {
                  ref
                      .read(billingControllerProvider.notifier)
                      .removeItemOverride(item.id!);
                  Navigator.of(ctx).pop();
                  _snack('Reset ${item.itemName} to original');
                },
                child: const Text('Reset',
                    style: TextStyle(color: WaiterTheme.errorRed)),
              ),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Cancel',
                  style: TextStyle(color: WaiterTheme.textMuted)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: WaiterTheme.primary,
                foregroundColor: Colors.white,
              ),
              onPressed: () {
                if (formKey.currentState?.validate() ?? false) {
                  final newQty =
                      int.tryParse(qtyCtrl.text.trim()) ?? item.quantityBilled;
                  final newPrice = double.tryParse(priceCtrl.text.trim()) ??
                      item.unitPriceSnapshot;
                  final reason = reasonCtrl.text.trim();
                  if (item.id != null) {
                    ref
                        .read(billingControllerProvider.notifier)
                        .setItemOverride(
                          item.id!,
                          ItemOverride(
                              unitPrice: newPrice,
                              quantity: newQty,
                              reason: reason),
                        );
                  }
                  Navigator.of(ctx).pop();
                  _snack('${item.itemName} updated');
                }
              },
              child: const Text('Apply'),
            ),
          ],
        );
      }),
    );
  }

  /// Add / edit a custom ad-hoc item (not in menu).
  void _showCustomItemDialog({int? editIndex, CustomItem? existing}) {
    final nameCtrl = TextEditingController(text: existing?.name ?? '');
    final qtyCtrl =
        TextEditingController(text: (existing?.quantity ?? 1).toString());
    final priceCtrl = TextEditingController(
        text: existing != null ? existing.unitPrice.toStringAsFixed(2) : '');
    final formKey = GlobalKey<FormState>();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setDS) {
        final p = double.tryParse(priceCtrl.text) ?? 0.0;
        final q = int.tryParse(qtyCtrl.text) ?? 1;
        final liveTotal = p * q;

        return AlertDialog(
          backgroundColor: WaiterTheme.surface,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Row(children: [
            const Icon(Icons.add_shopping_cart, color: WaiterTheme.primary),
            const SizedBox(width: 10),
            Text(
              editIndex != null ? 'Edit Custom Item' : 'Add Custom Item',
              style: const TextStyle(
                  color: WaiterTheme.textPrimary,
                  fontSize: 16,
                  fontWeight: FontWeight.bold),
            ),
          ]),
          content: Form(
            key: formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'For items not on the menu (e.g. milk, water, service)',
                    style: TextStyle(
                        color: WaiterTheme.textMuted, fontSize: 12),
                  ),
                  const SizedBox(height: 14),

                  // Name
                  const Text('Item Name',
                      style: TextStyle(
                          color: WaiterTheme.textSecondary,
                          fontSize: 12,
                          fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  TextFormField(
                    controller: nameCtrl,
                    textCapitalization: TextCapitalization.words,
                    style: const TextStyle(
                        color: WaiterTheme.textPrimary, fontSize: 15),
                    decoration: _inputDec(null).copyWith(
                        hintText: 'e.g. Fresh Milk, Mineral Water …',
                        hintStyle: const TextStyle(
                            color: WaiterTheme.textMuted, fontSize: 12)),
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) {
                        return 'Item name is required';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 14),

                  // Qty row
                  const Text('Quantity',
                      style: TextStyle(
                          color: WaiterTheme.textSecondary,
                          fontSize: 12,
                          fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      _qtyButton(Icons.remove, () {
                        final v = (int.tryParse(qtyCtrl.text) ?? 1) - 1;
                        if (v >= 1) {
                          qtyCtrl.text = v.toString();
                          setDS(() {});
                        }
                      }),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextFormField(
                          controller: qtyCtrl,
                          keyboardType: TextInputType.number,
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly
                          ],
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                              color: WaiterTheme.textPrimary,
                              fontSize: 20,
                              fontWeight: FontWeight.bold),
                          decoration: _inputDec(null),
                          onChanged: (_) => setDS(() {}),
                          validator: (v) {
                            final n = int.tryParse(v ?? '');
                            if (n == null || n < 1) return 'Min qty is 1';
                            return null;
                          },
                        ),
                      ),
                      const SizedBox(width: 8),
                      _qtyButton(Icons.add, () {
                        final v = (int.tryParse(qtyCtrl.text) ?? 0) + 1;
                        qtyCtrl.text = v.toString();
                        setDS(() {});
                      }),
                    ],
                  ),
                  const SizedBox(height: 14),

                  // Unit price
                  const Text('Unit Price (₹)',
                      style: TextStyle(
                          color: WaiterTheme.textSecondary,
                          fontSize: 12,
                          fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  TextFormField(
                    controller: priceCtrl,
                    keyboardType: const TextInputType.numberWithOptions(
                        decimal: true),
                    style: const TextStyle(
                        color: WaiterTheme.textPrimary, fontSize: 16),
                    decoration: _inputDec('₹'),
                    onChanged: (_) => setDS(() {}),
                    validator: (v) {
                      final n = double.tryParse(v ?? '');
                      if (n == null || n <= 0) {
                        return 'Enter a valid price > 0';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 12),

                  // Live total
                  if (liveTotal > 0)
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: WaiterTheme.primary.withOpacity(0.10),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                            color:
                                WaiterTheme.primary.withOpacity(0.35)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Line Total:',
                              style: TextStyle(
                                  color: WaiterTheme.textSecondary,
                                  fontSize: 13)),
                          Text(
                            CurrencyFormatter.format(liveTotal),
                            style: const TextStyle(
                              color: WaiterTheme.primary,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
          actions: [
            if (editIndex != null)
              TextButton(
                onPressed: () {
                  ref
                      .read(billingControllerProvider.notifier)
                      .removeCustomItem(editIndex);
                  Navigator.of(ctx).pop();
                  _snack('Custom item removed');
                },
                child: const Text('Remove',
                    style: TextStyle(color: WaiterTheme.errorRed)),
              ),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Cancel',
                  style: TextStyle(color: WaiterTheme.textMuted)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: WaiterTheme.primary,
                foregroundColor: Colors.white,
              ),
              onPressed: () {
                if (formKey.currentState?.validate() ?? false) {
                  final item = CustomItem(
                    name: nameCtrl.text.trim(),
                    quantity: int.tryParse(qtyCtrl.text.trim()) ?? 1,
                    unitPrice: double.tryParse(priceCtrl.text.trim()) ?? 0,
                  );
                  final notifier =
                      ref.read(billingControllerProvider.notifier);
                  if (editIndex != null) {
                    notifier.updateCustomItem(editIndex, item);
                    _snack('${item.name} updated');
                  } else {
                    notifier.addCustomItem(item);
                    _snack('${item.name} added to bill');
                  }
                  Navigator.of(ctx).pop();
                }
              },
              child:
                  Text(editIndex != null ? 'Update' : 'Add to Bill'),
            ),
          ],
        );
      }),
    );
  }

  /// Discount dialog – supports flat ₹ or % for both preview and issued bill.
  void _showDiscountDialog({
    required double subtotal,
    required bool isIssued,
    String? billId,
  }) {
    final st = ref.read(billingControllerProvider);
    final amtCtrl = TextEditingController(
        text: st.discountAmount > 0 ? st.discountAmount.toStringAsFixed(2) : '');
    final reasonCtrl = TextEditingController(
        text: st.discountReason?.isNotEmpty == true
            ? st.discountReason!
            : 'Courtesy discount');
    bool isPct = false;
    final formKey = GlobalKey<FormState>();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setDS) {
        final inputVal = double.tryParse(amtCtrl.text) ?? 0.0;
        final calcDisc = isPct
            ? (subtotal * inputVal / 100.0).clamp(0.0, subtotal)
            : inputVal.clamp(0.0, subtotal);

        return AlertDialog(
          backgroundColor: WaiterTheme.surface,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Row(
            children: [
              Icon(Icons.local_offer_outlined, color: WaiterTheme.primary),
              SizedBox(width: 10),
              Text('Add / Edit Discount',
                  style: TextStyle(
                      color: WaiterTheme.textPrimary,
                      fontSize: 16,
                      fontWeight: FontWeight.bold)),
            ],
          ),
          content: Form(
            key: formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _infoChip('Subtotal', CurrencyFormatter.format(subtotal)),
                  const SizedBox(height: 14),
                  // Toggle
                  Row(
                    children: [
                      Expanded(
                          child: _toggleBtn('Flat (₹)', !isPct,
                              () => setDS(() => isPct = false))),
                      const SizedBox(width: 8),
                      Expanded(
                          child: _toggleBtn('Percent (%)', isPct,
                              () => setDS(() => isPct = true))),
                    ],
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: amtCtrl,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    style: const TextStyle(
                        color: WaiterTheme.textPrimary, fontSize: 16),
                    decoration: _inputDec(isPct ? '%' : '₹'),
                    onChanged: (_) => setDS(() {}),
                    validator: (v) {
                      final n = double.tryParse(v ?? '');
                      if (n == null || n <= 0) return 'Enter a positive value';
                      if (isPct && n > 100) return 'Cannot exceed 100%';
                      if (!isPct && n > subtotal) {
                        return 'Cannot exceed subtotal';
                      }
                      return null;
                    },
                  ),
                  if (isPct && calcDisc > 0)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        '= ${CurrencyFormatter.format(calcDisc)}',
                        style: const TextStyle(
                            color: WaiterTheme.availableGreen,
                            fontWeight: FontWeight.bold),
                      ),
                    ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: reasonCtrl,
                    style: const TextStyle(
                        color: WaiterTheme.textPrimary, fontSize: 14),
                    decoration: _inputDec(null).copyWith(
                      hintText: 'Reason e.g. regular customer …',
                      hintStyle: const TextStyle(
                          color: WaiterTheme.textMuted, fontSize: 12),
                    ),
                    validator: (v) {
                      if (v == null || v.trim().length < 3) {
                        return 'Reason is required (min 3 chars)';
                      }
                      return null;
                    },
                  ),
                ],
              ),
            ),
          ),
          actions: [
            if (st.discountAmount > 0)
              TextButton(
                onPressed: () async {
                  Navigator.of(ctx).pop();
                  if (isIssued && billId != null) {
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
                  _snack('Discount removed');
                },
                child: const Text('Remove',
                    style: TextStyle(color: WaiterTheme.errorRed)),
              ),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Cancel',
                  style: TextStyle(color: WaiterTheme.textMuted)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: WaiterTheme.primary,
                foregroundColor: Colors.white,
              ),
              onPressed: () async {
                if (formKey.currentState?.validate() ?? false) {
                  Navigator.of(ctx).pop();
                  final reason = reasonCtrl.text.trim();
                  if (isIssued && billId != null) {
                    await ref
                        .read(billingControllerProvider.notifier)
                        .applyDiscountToIssuedBill(
                          billId: billId,
                          discountAmount: calcDisc,
                          reason: reason,
                        );
                  } else {
                    ref
                        .read(billingControllerProvider.notifier)
                        .setDiscount(calcDisc, reason);
                  }
                  _snack('Discount of ${CurrencyFormatter.format(calcDisc)} applied');
                }
              },
              child: const Text('Apply Discount'),
            ),
          ],
        );
      }),
    );
  }

  void _showGenerateConfirm(BillingState st, double grandTotal) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: WaiterTheme.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(
          'Generate Bill — Table ${widget.tableNumber}',
          style: const TextStyle(
              color: WaiterTheme.textPrimary, fontWeight: FontWeight.bold),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Grand Total: ${CurrencyFormatter.format(grandTotal)}',
              style: const TextStyle(
                  color: WaiterTheme.primary,
                  fontSize: 22,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            if (st.itemOverrides.isNotEmpty)
              Text(
                '• ${st.itemOverrides.length} item override(s) included',
                style:
                    const TextStyle(color: WaiterTheme.availableGreen, fontSize: 13),
              ),
            if (st.discountAmount > 0)
              Text(
                '• Discount: ${CurrencyFormatter.format(st.discountAmount)}',
                style:
                    const TextStyle(color: WaiterTheme.availableGreen, fontSize: 13),
              ),
            const SizedBox(height: 12),
            const Text(
              'Once generated, ordering for this table will be locked.',
              style:
                  TextStyle(color: WaiterTheme.textSecondary, fontSize: 13),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child:
                const Text('Cancel', style: TextStyle(color: WaiterTheme.textMuted)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: WaiterTheme.primary,
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              Navigator.of(ctx).pop();
              final bill = await ref
                  .read(billingControllerProvider.notifier)
                  .generateBill(tableNumber: widget.tableNumber);
              if (bill != null && mounted) {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(
                      builder: (_) => PaymentRecordingScreen(bill: bill)),
                );
              }
            },
            child: const Text('Confirm & Generate'),
          ),
        ],
      ),
    );
  }

  // ────────────────────────────────────────────────────────────────────────────
  // Build
  // ────────────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final st = ref.watch(billingControllerProvider);
    final tableBill = st.tableBill;
    final bill = st.bill;

    return Scaffold(
      backgroundColor: WaiterTheme.background,
      appBar: AppBar(
        title: Text('Bill Preview — Table ${widget.tableNumber}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: () => ref
                .read(billingControllerProvider.notifier)
                .loadTableBill(widget.tableNumber),
          ),
        ],
      ),
      body: st.isLoading
          ? const Center(child: CircularProgressIndicator())
          : st.error != null
              ? _buildError(st.error!)
              : tableBill == null
                  ? const Center(
                      child: Text('No billing information available',
                          style: TextStyle(color: WaiterTheme.textMuted)))
                  : _buildBody(st, tableBill, bill),
    );
  }

  Widget _buildError(String msg) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline,
                  size: 48, color: WaiterTheme.errorRed),
              const SizedBox(height: 12),
              Text(msg,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      color: WaiterTheme.errorRed, fontSize: 15)),
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
      );

  Widget _buildBody(
      BillingState st, TableBillModel tableBill, BillModel? bill) {
    final isPreview = bill == null;
    // Always allow editing — even on ISSUED bills waiter can adjust and re-generate
    const canEdit = true;
    final items = isPreview ? tableBill.previewLineItems : bill.lineItems;

    // Live totals — always recalculate with any pending overrides
    double liveSubtotal = 0.0;
    for (final it in items) {
      final ov = st.itemOverrides[it.id];
      final p = ov?.unitPrice ?? it.unitPriceSnapshot;
      final q = ov?.quantity ?? it.quantityBilled;
      liveSubtotal += p * q;
    }
    // Add any pending custom items
    for (final ci in st.customItems) {
      liveSubtotal += ci.lineTotal;
    }
    // If no overrides/custom items yet and bill is issued, use the frozen subtotal
    if (!isPreview && st.itemOverrides.isEmpty && st.customItems.isEmpty) {
      liveSubtotal = bill.subtotalAmount;
    }

    final liveDiscount =
        isPreview ? st.discountAmount : bill.discountAmount;
    final liveDiscountReason =
        isPreview ? st.discountReason : bill.discountReason;
    final liveTaxable =
        (liveSubtotal - liveDiscount).clamp(0.0, double.infinity);
    final liveCgst = liveTaxable * 0.025;
    final liveSgst = liveTaxable * 0.025;
    final liveGrandTotal = liveTaxable + liveCgst + liveSgst;

    return Column(
      children: [
        // ── Warnings ──────────────────────────────────────────────────
        if (tableBill.hasUnacceptedPlacedOrders)
          _warningBanner(
              Icons.warning_amber_rounded,
              const Color(0xFFC2410C),
              Colors.red,
              'Unaccepted PLACED orders exist — kitchen must accept/reject first.'),
        if (!tableBill.hasUnacceptedPlacedOrders &&
            tableBill.hasUnservedOrders)
          _warningBanner(
              Icons.info_outline,
              const Color(0xFFB45309),
              Colors.amber,
              'Some orders not yet SERVED. Bill can still be generated.'),

        // ── Main scrollable content ────────────────────────────────────
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 6),
            children: [
              _buildHeaderCard(tableBill, bill),
              const SizedBox(height: 14),

              // ── Editable Item Table ──────────────────────────────────
              _buildItemTable(st, items, canEdit),
              const SizedBox(height: 10),

              // ── Custom (ad-hoc) items section ────────────────────────
              _buildCustomItemsSection(st),
              const SizedBox(height: 14),

              // ── Financial summary ────────────────────────────────────
              _buildFinancialSummary(
                st: st,
                subtotal: liveSubtotal,
                discount: liveDiscount,
                discountReason: liveDiscountReason,
                taxable: liveTaxable,
                cgst: liveCgst,
                sgst: liveSgst,
                grandTotal: liveGrandTotal,
                isIssued: !isPreview,
                billId: bill?.id,
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),

        // ── Bottom action bar ──────────────────────────────────────────
        _buildActionBar(st, tableBill, bill, liveGrandTotal),
      ],
    );
  }

  // ── Custom items section ─────────────────────────────────────────────────────
  Widget _buildCustomItemsSection(BillingState st) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Existing custom rows
        if (st.customItems.isNotEmpty)
          Container(
            decoration: BoxDecoration(
              color: WaiterTheme.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: WaiterTheme.primary.withOpacity(0.4)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: WaiterTheme.primary.withOpacity(0.08),
                    borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.add_shopping_cart,
                          size: 14, color: WaiterTheme.primary),
                      const SizedBox(width: 6),
                      const Expanded(
                        child: Text('CUSTOM ITEMS',
                            style: TextStyle(
                                color: WaiterTheme.primary,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 0.8)),
                      ),
                      Text('${st.customItems.length} added',
                          style: const TextStyle(
                              color: WaiterTheme.textMuted, fontSize: 11)),
                    ],
                  ),
                ),
                const Divider(color: WaiterTheme.surfaceVariant, height: 1),
                ...st.customItems.asMap().entries.map((e) {
                  final idx = e.key;
                  final ci = e.value;
                  return Column(
                    children: [
                      if (idx > 0)
                        const Divider(
                            color: WaiterTheme.surfaceVariant,
                            height: 1,
                            indent: 14),
                      InkWell(
                        onTap: () => _showCustomItemDialog(
                            editIndex: idx, existing: ci),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 10),
                          child: Row(
                            children: [
                              Expanded(
                                flex: 5,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(children: [
                                      Container(
                                        margin: const EdgeInsets.only(right: 5),
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 4, vertical: 1),
                                        decoration: BoxDecoration(
                                          color: WaiterTheme.primary
                                              .withOpacity(0.15),
                                          borderRadius:
                                              BorderRadius.circular(3),
                                        ),
                                        child: const Text('CUSTOM',
                                            style: TextStyle(
                                                color: WaiterTheme.primary,
                                                fontSize: 9,
                                                fontWeight: FontWeight.bold)),
                                      ),
                                      Expanded(
                                        child: Text(ci.name,
                                            style: const TextStyle(
                                                color: WaiterTheme.textPrimary,
                                                fontSize: 14,
                                                fontWeight: FontWeight.w600)),
                                      ),
                                    ]),
                                    const Text('Not in menu',
                                        style: TextStyle(
                                            color: WaiterTheme.textMuted,
                                            fontSize: 11)),
                                  ],
                                ),
                              ),
                              SizedBox(
                                width: 52,
                                child: Center(
                                  child: Text('${ci.quantity}',
                                      style: const TextStyle(
                                          color: WaiterTheme.textPrimary,
                                          fontSize: 15,
                                          fontWeight: FontWeight.bold)),
                                ),
                              ),
                              SizedBox(
                                width: 72,
                                child: Center(
                                  child: Text(
                                      '₹${ci.unitPrice.toStringAsFixed(2)}',
                                      style: const TextStyle(
                                          color: WaiterTheme.textSecondary,
                                          fontSize: 13)),
                                ),
                              ),
                              SizedBox(
                                width: 72,
                                child: Align(
                                  alignment: Alignment.centerRight,
                                  child: Text(
                                      CurrencyFormatter.format(ci.lineTotal),
                                      style: const TextStyle(
                                          color: WaiterTheme.primary,
                                          fontSize: 14,
                                          fontWeight: FontWeight.bold)),
                                ),
                              ),
                              SizedBox(
                                width: 36,
                                child: Center(
                                  child: IconButton(
                                    icon: const Icon(Icons.edit_outlined,
                                        size: 18, color: WaiterTheme.primary),
                                    padding: EdgeInsets.zero,
                                    constraints: const BoxConstraints(),
                                    onPressed: () => _showCustomItemDialog(
                                        editIndex: idx, existing: ci),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  );
                }),
              ],
            ),
          ),
        const SizedBox(height: 8),

        // Add custom item button
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            icon: const Icon(Icons.add, size: 18),
            label: const Text('Add Custom Item to Bill'),
            style: OutlinedButton.styleFrom(
              foregroundColor: WaiterTheme.primary,
              side: const BorderSide(color: WaiterTheme.primary),
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10)),
            ),
            onPressed: () => _showCustomItemDialog(),
          ),
        ),
      ],
    );
  }

  // ── Item table ───────────────────────────────────────────────────────────────
  Widget _buildItemTable(
      BillingState st, List<BillItemModel> items, bool isPreview) {
    return Container(
      decoration: BoxDecoration(
        color: WaiterTheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: WaiterTheme.surfaceVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: WaiterTheme.surfaceVariant,
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(12)),
            ),
            child: Row(
              children: [
                const Expanded(
                  flex: 5,
                  child: Text('ITEM',
                      style: TextStyle(
                          color: WaiterTheme.textMuted,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.8)),
                ),
                const SizedBox(
                  width: 52,
                  child: Center(
                    child: Text('QTY',
                        style: TextStyle(
                            color: WaiterTheme.textMuted,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.8)),
                  ),
                ),
                const SizedBox(
                  width: 72,
                  child: Center(
                    child: Text('UNIT ₹',
                        style: TextStyle(
                            color: WaiterTheme.textMuted,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.8)),
                  ),
                ),
                const SizedBox(
                  width: 72,
                  child: Align(
                    alignment: Alignment.centerRight,
                    child: Text('TOTAL',
                        style: TextStyle(
                            color: WaiterTheme.textMuted,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.8)),
                  ),
                ),
                if (isPreview) const SizedBox(width: 36),
              ],
            ),
          ),
          const Divider(color: WaiterTheme.surfaceVariant, height: 1),

          // Item rows
          if (items.isEmpty)
            const Padding(
              padding: EdgeInsets.all(20),
              child: Center(
                child: Text('No active billable items.',
                    style: TextStyle(color: WaiterTheme.textMuted)),
              ),
            )
          else
            ...items.asMap().entries.map((entry) {
              final idx = entry.key;
              final item = entry.value;
              final ov = st.itemOverrides[item.id];
              final dispPrice = ov?.unitPrice ?? item.unitPriceSnapshot;
              final dispQty = ov?.quantity ?? item.quantityBilled;
              final dispTotal = dispPrice * dispQty;
              final modified = ov != null;

              return Column(
                children: [
                  if (idx > 0)
                    const Divider(
                        color: WaiterTheme.surfaceVariant, height: 1, indent: 14),
                  InkWell(
                    onTap: isPreview
                        ? () => _showEditItemDialog(item, st)
                        : null,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 10),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          // Name + variant
                          Expanded(
                            flex: 5,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    if (modified)
                                      Container(
                                        margin:
                                            const EdgeInsets.only(right: 5),
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 4, vertical: 1),
                                        decoration: BoxDecoration(
                                          color: WaiterTheme.primary
                                              .withOpacity(0.18),
                                          borderRadius:
                                              BorderRadius.circular(3),
                                        ),
                                        child: const Text('EDITED',
                                            style: TextStyle(
                                                color: WaiterTheme.primary,
                                                fontSize: 9,
                                                fontWeight: FontWeight.bold)),
                                      ),
                                    Expanded(
                                      child: Text(
                                        item.itemName,
                                        style: TextStyle(
                                          color: modified
                                              ? WaiterTheme.textPrimary
                                              : WaiterTheme.textPrimary,
                                          fontSize: 14,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                Text(
                                  '${item.variantName}  •  ${item.unit}',
                                  style: const TextStyle(
                                      color: WaiterTheme.textMuted, fontSize: 11),
                                ),
                                if (modified && ov.reason.isNotEmpty)
                                  Text(
                                    ov.reason,
                                    style: const TextStyle(
                                        color: WaiterTheme.primary,
                                        fontSize: 11,
                                        fontStyle: FontStyle.italic),
                                  ),
                              ],
                            ),
                          ),

                          // Qty
                          SizedBox(
                            width: 52,
                            child: Center(
                              child: Column(
                                children: [
                                  Text(
                                    '$dispQty',
                                    style: TextStyle(
                                      color: modified
                                          ? WaiterTheme.primary
                                          : WaiterTheme.textPrimary,
                                      fontSize: 15,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  if (modified &&
                                      dispQty != item.quantityBilled)
                                    Text(
                                      '(${item.quantityBilled})',
                                      style: const TextStyle(
                                          color: WaiterTheme.textMuted,
                                          fontSize: 10,
                                          decoration:
                                              TextDecoration.lineThrough),
                                    ),
                                ],
                              ),
                            ),
                          ),

                          // Unit price
                          SizedBox(
                            width: 72,
                            child: Center(
                              child: Column(
                                children: [
                                  Text(
                                    '₹${dispPrice.toStringAsFixed(2)}',
                                    style: TextStyle(
                                      color: modified
                                          ? WaiterTheme.primary
                                          : WaiterTheme.textSecondary,
                                      fontSize: 13,
                                      fontWeight: modified
                                          ? FontWeight.bold
                                          : FontWeight.normal,
                                    ),
                                  ),
                                  if (modified &&
                                      dispPrice != item.unitPriceSnapshot)
                                    Text(
                                      '₹${item.unitPriceSnapshot.toStringAsFixed(2)}',
                                      style: const TextStyle(
                                          color: WaiterTheme.textMuted,
                                          fontSize: 10,
                                          decoration:
                                              TextDecoration.lineThrough),
                                    ),
                                ],
                              ),
                            ),
                          ),

                          // Line total
                          SizedBox(
                            width: 72,
                            child: Align(
                              alignment: Alignment.centerRight,
                              child: Text(
                                CurrencyFormatter.format(dispTotal),
                                style: TextStyle(
                                  color: modified
                                      ? WaiterTheme.primary
                                      : WaiterTheme.textPrimary,
                                  fontSize: 14,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ),

                          // Edit button
                          if (isPreview)
                            SizedBox(
                              width: 36,
                              child: Center(
                                child: IconButton(
                                  icon: Icon(
                                    modified
                                        ? Icons.edit
                                        : Icons.edit_outlined,
                                    size: 18,
                                    color: modified
                                        ? WaiterTheme.primary
                                        : WaiterTheme.textMuted,
                                  ),
                                  padding: EdgeInsets.zero,
                                  constraints: const BoxConstraints(),
                                  tooltip: 'Edit price / qty',
                                  onPressed: () =>
                                      _showEditItemDialog(item, st),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            }),
        ],
      ),
    );
  }

  // ── Financial summary ────────────────────────────────────────────────────────
  Widget _buildFinancialSummary({
    required BillingState st,
    required double subtotal,
    required double discount,
    required String? discountReason,
    required double taxable,
    required double cgst,
    required double sgst,
    required double grandTotal,
    required bool isIssued,
    String? billId,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: WaiterTheme.surfaceVariant),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Financial Summary',
                  style: TextStyle(
                      color: WaiterTheme.textPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.bold)),
              // Discount button
              InkWell(
                onTap: () => _showDiscountDialog(
                    subtotal: subtotal, isIssued: isIssued, billId: billId),
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: discount > 0
                        ? WaiterTheme.availableGreen.withOpacity(0.15)
                        : WaiterTheme.primary.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                        color: discount > 0
                            ? WaiterTheme.availableGreen
                            : WaiterTheme.primary),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.local_offer,
                          size: 13,
                          color: discount > 0
                              ? WaiterTheme.availableGreen
                              : WaiterTheme.primary),
                      const SizedBox(width: 4),
                      Text(
                        discount > 0 ? 'Edit Discount' : '+ Discount',
                        style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: discount > 0
                                ? WaiterTheme.availableGreen
                                : WaiterTheme.primary),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const Divider(color: WaiterTheme.surfaceVariant, height: 16),
          _summaryRow('Item Subtotal', CurrencyFormatter.format(subtotal)),
          if (discount > 0) ...[
            _summaryRow(
              'Discount${discountReason != null ? ' ($discountReason)' : ''}',
              '− ${CurrencyFormatter.format(discount)}',
              valueColor: WaiterTheme.availableGreen,
            ),
          ],
          _summaryRow('Taxable Amount', CurrencyFormatter.format(taxable)),
          _summaryRow('CGST (2.5%)', CurrencyFormatter.format(cgst)),
          _summaryRow('SGST (2.5%)', CurrencyFormatter.format(sgst)),
          const Divider(color: WaiterTheme.surfaceVariant, height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Grand Total',
                  style: TextStyle(
                      color: WaiterTheme.textPrimary,
                      fontSize: 18,
                      fontWeight: FontWeight.bold)),
              Text(
                CurrencyFormatter.format(grandTotal),
                style: const TextStyle(
                    color: WaiterTheme.primary,
                    fontSize: 22,
                    fontWeight: FontWeight.bold),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ── Header card ──────────────────────────────────────────────────────────────
  Widget _buildHeaderCard(TableBillModel tb, BillModel? bill) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: WaiterTheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: WaiterTheme.surfaceVariant),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Table ${tb.tableNumber}',
                  style: const TextStyle(
                      color: WaiterTheme.textPrimary,
                      fontSize: 20,
                      fontWeight: FontWeight.bold)),
              if (tb.tableDisplayName != null)
                Text(tb.tableDisplayName!,
                    style: const TextStyle(
                        color: WaiterTheme.textSecondary, fontSize: 13)),
              Text(
                bill != null
                    ? 'Bill #${bill.billNumber}'
                    : 'Session: ${tb.sessionCode}',
                style: const TextStyle(color: WaiterTheme.textMuted, fontSize: 12),
              ),
            ],
          ),
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: bill != null
                  ? WaiterTheme.availableGreen.withOpacity(0.2)
                  : Colors.orange.withOpacity(0.2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              bill != null ? bill.status : 'PREVIEW',
              style: TextStyle(
                color: bill != null
                    ? WaiterTheme.availableGreen
                    : const Color(0xFFC2410C),
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ── Bottom action bar ────────────────────────────────────────────────────────
  Widget _buildActionBar(
      BillingState st, TableBillModel tb, BillModel? bill, double grandTotal) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: const BoxDecoration(
        color: WaiterTheme.surfaceVariant,
        border: Border(top: BorderSide(color: WaiterTheme.surfaceVariant)),
      ),
      child: bill != null
          ? Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // If waiter has pending overrides on an issued bill → offer re-generate
                if (st.itemOverrides.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: ElevatedButton.icon(
                        icon: st.isSubmitting
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                    color: Colors.white, strokeWidth: 2))
                            : const Icon(Icons.receipt_long, size: 18),
                        label: Text(
                          'Apply Changes & Re-generate  ${CurrencyFormatter.format(grandTotal)}',
                          style: const TextStyle(
                              fontSize: 14, fontWeight: FontWeight.bold),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: WaiterTheme.primary,
                          foregroundColor: Colors.white,
                        ),
                        onPressed: st.isSubmitting
                            ? null
                            : () => _showGenerateConfirm(st, grandTotal),
                      ),
                    ),
                  ),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton.icon(
                    icon: const Icon(Icons.payment),
                    label: Text(
                      'Record Payment  ${CurrencyFormatter.format(bill.grandTotal)}',
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: WaiterTheme.availableGreen,
                      foregroundColor: Colors.white,
                    ),
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(
                          builder: (_) => PaymentRecordingScreen(bill: bill)),
                    ),
                  ),
                ),
              ],
            )
          : SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                icon: st.isSubmitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : const Icon(Icons.receipt_long),
                label: Text(
                  'Generate Final Bill  ${CurrencyFormatter.format(grandTotal)}',
                  style: const TextStyle(
                      fontSize: 16, fontWeight: FontWeight.bold),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: tb.canGenerateBill && !st.isSubmitting
                      ? WaiterTheme.primary
                      : Colors.grey.shade700,
                  foregroundColor: Colors.white,
                ),
                onPressed: tb.canGenerateBill && !st.isSubmitting
                    ? () => _showGenerateConfirm(st, grandTotal)
                    : null,
              ),
            ),
    );
  }

  // ── Small helpers ────────────────────────────────────────────────────────────

  Widget _warningBanner(
      IconData icon, Color fg, MaterialColor bg, String msg) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
      color: bg.withOpacity(0.14),
      child: Row(
        children: [
          Icon(icon, color: fg, size: 18),
          const SizedBox(width: 8),
          Expanded(
              child: Text(msg,
                  style: TextStyle(color: fg, fontSize: 12))),
        ],
      ),
    );
  }

  Widget _infoChip(String label, String value) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: WaiterTheme.surfaceVariant,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: WaiterTheme.surfaceVariant),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: const TextStyle(
                  color: WaiterTheme.textSecondary, fontSize: 13)),
          Text(value,
              style: const TextStyle(
                  color: WaiterTheme.textPrimary, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  InputDecoration _inputDec(String? prefix) {
    return InputDecoration(
      prefixText: prefix != null ? '$prefix  ' : null,
      prefixStyle:
          const TextStyle(color: WaiterTheme.primary, fontWeight: FontWeight.bold),
      filled: true,
      fillColor: WaiterTheme.surfaceVariant,
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
      enabledBorder: OutlineInputBorder(
        borderSide: const BorderSide(color: WaiterTheme.surfaceVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      focusedBorder: OutlineInputBorder(
        borderSide: const BorderSide(color: WaiterTheme.primary, width: 1.5),
        borderRadius: BorderRadius.circular(8),
      ),
      errorBorder: OutlineInputBorder(
        borderSide: const BorderSide(color: WaiterTheme.errorRed),
        borderRadius: BorderRadius.circular(8),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderSide: const BorderSide(color: WaiterTheme.errorRed, width: 1.5),
        borderRadius: BorderRadius.circular(8),
      ),
    );
  }

  Widget _qtyButton(IconData icon, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: WaiterTheme.surfaceVariant,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: WaiterTheme.surfaceVariant),
        ),
        child: Icon(icon, color: WaiterTheme.primary, size: 20),
      ),
    );
  }

  Widget _toggleBtn(String label, bool active, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: active ? WaiterTheme.primary : WaiterTheme.surfaceVariant,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
              color: active ? WaiterTheme.primary : WaiterTheme.surfaceVariant),
        ),
        child: Center(
          child: Text(
            label,
            style: TextStyle(
              color: active ? Colors.white : WaiterTheme.textSecondary,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),
        ),
      ),
    );
  }

  Widget _summaryRow(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Text(label,
                style: const TextStyle(
                    color: WaiterTheme.textSecondary, fontSize: 13)),
          ),
          Text(value,
              style: TextStyle(
                  color: valueColor ?? WaiterTheme.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  void _snack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
          content: Text(msg),
          backgroundColor: WaiterTheme.surfaceVariant,
          duration: const Duration(seconds: 2)),
    );
  }
}
