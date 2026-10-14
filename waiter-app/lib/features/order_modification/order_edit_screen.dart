import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../core/network/api_client.dart';
import '../../core/network/api_exceptions.dart';
import '../../core/utils/currency_formatter.dart';
import '../../models/order_model.dart';
import '../auth/auth_controller.dart';
import 'force_cancel_dialog.dart';

class OrderEditScreen extends ConsumerStatefulWidget {
  final OrderModel order;

  const OrderEditScreen({
    Key? key,
    required this.order,
  }) : super(key: key);

  @override
  ConsumerState<OrderEditScreen> createState() => _OrderEditScreenState();
}

class _OrderEditScreenState extends ConsumerState<OrderEditScreen> {
  late Map<String, int> _quantities;
  final _reasonController = TextEditingController();
  bool _isSubmitting = false;
  // Waiter override: allows REDUCING / REMOVING items while the kitchen is PREPARING.
  bool _force = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _quantities = {
      for (var item in widget.order.items) item.id: item.quantity,
    };
  }

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  bool get _isPreparing => widget.order.status == 'PREPARING';
  bool get _isReady => widget.order.status == 'READY';

  /// Lowest quantity a line may be set to right now.
  /// While PREPARING you can only add, unless the waiter switches FORCE on.
  int _minQty(OrderItemModel item) => (_isPreparing && !_force) ? item.quantity : 0;

  bool get _hasReduction {
    for (var item in widget.order.items) {
      if ((_quantities[item.id] ?? item.quantity) < item.quantity) return true;
    }
    return false;
  }

  bool get _requiresReason =>
      widget.order.status == 'ACCEPTED' || widget.order.status == 'PREPARING';

  double get _projectedSubtotal {
    double total = 0.0;
    for (var item in widget.order.items) {
      final q = _quantities[item.id] ?? item.quantity;
      total += item.unitPrice * q;
    }
    return total;
  }

  double get _priceDelta => _projectedSubtotal - widget.order.subtotal;

  bool get _hasChanges {
    for (var item in widget.order.items) {
      if ((_quantities[item.id] ?? item.quantity) != item.quantity) {
        return true;
      }
    }
    return false;
  }

  Future<void> _submitModification() async {
    if (!_hasChanges) {
      Navigator.of(context).pop(false);
      return;
    }

    final forcing = _isPreparing && _hasReduction && _force;
    if (forcing && _reasonController.text.trim().length < 3) {
      setState(() {
        _errorMessage = 'A forced change needs a reason (at least 3 characters).';
      });
      return;
    }

    if (_requiresReason && _reasonController.text.trim().isEmpty) {
      setState(() {
        _errorMessage =
            'Modification reason is mandatory for in-progress kitchen orders.';
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final itemsPayload = widget.order.items
          .where((item) => item.quantity > 0)
          .map((item) {
        return {
          'order_item_id': item.id,
          'new_quantity': _quantities[item.id] ?? item.quantity,
        };
      }).toList();

      final data = {
        'expected_version': widget.order.version,
        'items': itemsPayload,
        'reason': _reasonController.text.trim().isNotEmpty
            ? _reasonController.text.trim()
            : 'Updated by waiter',
        'force': forcing,
      };

      final apiClient = ref.read(apiClientProvider);
      await apiClient.patch('/api/v1/waiter/orders/${widget.order.id}',
          data: data);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Order updated successfully!'),
            backgroundColor: AppTheme.successColor,
          ),
        );
        Navigator.of(context).pop(true);
      }
    } on ConflictException catch (e) {
      setState(() {
        _errorMessage =
            'Concurrency Conflict: ${e.message}. Order was modified by another user. Please re-open.';
        _isSubmitting = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = describeError(e);
        _isSubmitting = false;
      });
    }
  }

  Future<void> _forceCancelOrder() async {
    final reason = await ForceCancelDialog.show(
      context,
      orderNumber: widget.order.orderNumber,
      status: widget.order.status,
    );
    if (reason == null) return;

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });
    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.post(
        '/api/v1/waiter/orders/${widget.order.id}/cancel',
        data: {
          'expected_version': widget.order.version,
          'cancellation_reason': reason,
          'force': true,
        },
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Order force-cancelled. Kitchen has been notified.'),
            backgroundColor: AppTheme.successColor,
          ),
        );
        Navigator.of(context).pop(true);
      }
    } on ConflictException catch (e) {
      setState(() {
        _errorMessage = 'Order changed meanwhile: ${e.message}. Please re-open.';
        _isSubmitting = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = describeError(e);
        _isSubmitting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: Text('Edit Order #${widget.order.orderNumber}'),
      ),
      body: Column(
        children: [
          if (_errorMessage != null)
            Container(
              padding: const EdgeInsets.all(12),
              color: AppTheme.errorColor.withOpacity(0.15),
              child: Row(
                children: [
                  const Icon(Icons.error_outline,
                      color: AppTheme.errorColor, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(
                          color: AppTheme.errorColor, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.cardColor,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.borderColor),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.info_outline,
                          color: AppTheme.accentColor, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _isReady
                              ? 'This order is READY. Items can no longer be edited - only a FORCE cancel is possible.'
                              : _isPreparing
                                  ? 'Kitchen is COOKING this. You can add more freely; reducing or removing needs FORCE (kitchen is alerted).'
                                  : _requiresReason
                                      ? 'This order is in Kitchen (${widget.order.status}). Adjusting quantities will alert kitchen staff.'
                                      : 'This order is PLACED. Items will be updated cleanly.',
                          style: const TextStyle(
                              color: AppTheme.textSecondary, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'Order Line Items',
                  style: TextStyle(
                    color: AppTheme.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                ...widget.order.items.map((item) {
                  final qty = _quantities[item.id] ?? item.quantity;
                  final isRemoved = qty == 0;
                  final lockedLine = item.quantity == 0 || _isReady;
                  final minQ = _minQty(item);

                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isRemoved
                          ? AppTheme.cardColor.withOpacity(0.5)
                          : AppTheme.cardColor,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: isRemoved
                            ? AppTheme.errorColor.withOpacity(0.3)
                            : AppTheme.borderColor,
                      ),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item.itemName,
                                style: TextStyle(
                                  color: isRemoved
                                      ? AppTheme.textMuted
                                      : AppTheme.textPrimary,
                                  fontWeight: FontWeight.w600,
                                  fontSize: 14,
                                  decoration: isRemoved
                                      ? TextDecoration.lineThrough
                                      : null,
                                ),
                              ),
                              if (item.variantName != null)
                                Text(
                                  item.variantName!,
                                  style: const TextStyle(
                                    color: AppTheme.textSecondary,
                                    fontSize: 12,
                                  ),
                                ),
                              const SizedBox(height: 4),
                              Text(
                                '${CurrencyFormatter.format(item.unitPrice)} each',
                                style: const TextStyle(
                                  color: AppTheme.accentColor,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Row(
                          children: [
                            IconButton(
                              icon: const Icon(Icons.remove_circle_outline),
                              color: (!lockedLine && qty > minQ)
                                  ? AppTheme.accentColor
                                  : AppTheme.textMuted,
                              tooltip: (_isPreparing && !_force && qty <= minQ)
                                  ? 'Cooking started - use FORCE to reduce'
                                  : null,
                              onPressed: (!lockedLine && qty > minQ)
                                  ? () {
                                      setState(() {
                                        _quantities[item.id] = qty - 1;
                                      });
                                    }
                                  : null,
                            ),
                            Container(
                              constraints: const BoxConstraints(minWidth: 28),
                              alignment: Alignment.center,
                              child: Text(
                                '$qty',
                                style: TextStyle(
                                  color: qty == 0
                                      ? AppTheme.errorColor
                                      : AppTheme.textPrimary,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 16,
                                ),
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.add_circle_outline),
                              color: lockedLine
                                  ? AppTheme.textMuted
                                  : AppTheme.accentColor,
                              onPressed: lockedLine || qty >= 20
                                  ? null
                                  : () {
                                      setState(() {
                                        _quantities[item.id] = qty + 1;
                                      });
                                    },
                            ),
                          ],
                        ),
                      ],
                    ),
                  );
                }),
                if (_isPreparing) ...[
                  const SizedBox(height: 8),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    activeColor: AppTheme.errorColor,
                    title: const Text('Force reduce / remove items',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontWeight: FontWeight.w600,
                            fontSize: 14)),
                    subtitle: const Text(
                        'Food may already be cooked. Kitchen will be alerted.',
                        style: TextStyle(
                            color: AppTheme.textSecondary, fontSize: 12)),
                    value: _force,
                    onChanged: _isSubmitting
                        ? null
                        : (v) {
                            setState(() {
                              _force = v;
                              if (!v) {
                                // snap any reductions back to the cooked quantity
                                for (var it in widget.order.items) {
                                  final cur = _quantities[it.id] ?? it.quantity;
                                  if (cur < it.quantity) {
                                    _quantities[it.id] = it.quantity;
                                  }
                                }
                              }
                            });
                          },
                  ),
                ],
                if (_isPreparing || _isReady) ...[
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    icon: const Icon(Icons.local_fire_department),
                    label: const Text('Force Cancel Entire Order'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.errorColor,
                      side: const BorderSide(color: AppTheme.errorColor),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    onPressed: _isSubmitting ? null : _forceCancelOrder,
                  ),
                ],
                if (_requiresReason && !_isReady) ...[
                  const SizedBox(height: 16),
                  const Text(
                    'Reason for Kitchen Modification *',
                    style: TextStyle(
                      color: AppTheme.textPrimary,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _reasonController,
                    maxLines: 2,
                    decoration: InputDecoration(
                      hintText:
                          'e.g. Guest requested 1 fewer naan, extra rice...',
                      filled: true,
                      fillColor: AppTheme.cardColor,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide:
                            const BorderSide(color: AppTheme.borderColor),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              color: AppTheme.surfaceColor,
              border: Border(top: BorderSide(color: AppTheme.borderColor)),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Original Subtotal:'),
                    Text(CurrencyFormatter.format(widget.order.subtotal)),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('New Subtotal:'),
                    Text(
                      CurrencyFormatter.format(_projectedSubtotal),
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
                if (_priceDelta != 0) ...[
                  const SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Change Delta:'),
                      Text(
                        '${_priceDelta > 0 ? '+' : ''}${CurrencyFormatter.format(_priceDelta)}',
                        style: TextStyle(
                          color: _priceDelta > 0
                              ? AppTheme.accentColor
                              : AppTheme.successColor,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ],
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.accentColor,
                      foregroundColor: Colors.white,
                    ),
                    onPressed: _isSubmitting || !_hasChanges || _isReady
                        ? null
                        : _submitModification,
                    child: _isSubmitting
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Text(
                            'Save Modifications',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
