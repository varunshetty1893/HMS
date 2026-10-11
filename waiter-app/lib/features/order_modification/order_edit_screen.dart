import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../core/network/api_client.dart';
import '../../core/network/api_exceptions.dart';
import '../../core/utils/currency_formatter.dart';
import '../../models/order_model.dart';
import '../auth/auth_controller.dart';

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
      final itemsPayload = widget.order.items.map((item) {
        return {
          'order_item_id': item.id,
          'new_quantity': _quantities[item.id] ?? item.quantity,
        };
      }).toList();

      final data = {
        'version': widget.order.version,
        'items': itemsPayload,
        if (_reasonController.text.trim().isNotEmpty)
          'modification_reason': _reasonController.text.trim(),
      };

      final apiClient = ref.read(apiClientProvider);
      await apiClient.patch('/api/v1/waiter/orders/${widget.order.id}', data: data);

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
        _errorMessage = e.toString();
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
                          _requiresReason
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
                              color: qty > 0
                                  ? AppTheme.accentColor
                                  : AppTheme.textMuted,
                              onPressed: qty > 0
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
                              color: AppTheme.accentColor,
                              onPressed: () {
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
                if (_requiresReason) ...[
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
                      foregroundColor: Colors.black,
                    ),
                    onPressed: _isSubmitting || !_hasChanges
                        ? null
                        : _submitModification,
                    child: _isSubmitting
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.black,
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
