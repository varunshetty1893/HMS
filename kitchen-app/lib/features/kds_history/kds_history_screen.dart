import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../core/network/api_client.dart';
import '../../models/kitchen_order_model.dart';

class KdsHistoryScreen extends ConsumerStatefulWidget {
  const KdsHistoryScreen({super.key});

  @override
  ConsumerState<KdsHistoryScreen> createState() => _KdsHistoryScreenState();
}

class _KdsHistoryScreenState extends ConsumerState<KdsHistoryScreen> {
  static const _pageSize = 30;
  final List<KitchenOrderModel> _orders = [];
  var _page = 0;
  var _hasMore = true;
  var _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadMore();
  }

  Future<void> _refresh() async {
    setState(() {
      _orders.clear();
      _page = 0;
      _hasMore = true;
      _error = null;
    });
    await _loadMore();
  }

  Future<void> _loadMore() async {
    if (_isLoading || !_hasMore) return;
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final data = await ref
          .read(apiClientProvider)
          .getOrderHistory(page: _page + 1, pageSize: _pageSize);
      if (!mounted) return;
      final next = data
          .map((e) => KitchenOrderModel.fromJson(e as Map<String, dynamic>))
          .toList();
      setState(() {
        _orders.addAll(next);
        _page++;
        _hasMore = next.length == _pageSize;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString().replaceFirst('ApiException: ', ''));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: KdsTheme.background,
        appBar: AppBar(
          title: const Text('Kitchen Order History'),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh),
              tooltip: 'Refresh history',
              onPressed: _isLoading ? null : _refresh,
            ),
          ],
        ),
        body: _buildBody(),
      );

  Widget _buildBody() {
    if (_isLoading && _orders.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _orders.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Failed to load history: $_error',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.redAccent)),
              const SizedBox(height: 12),
              ElevatedButton(onPressed: _loadMore, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }
    if (_orders.isEmpty) {
      return const Center(
        child: Text('No past orders in history',
            style: TextStyle(color: KdsTheme.textMuted)),
      );
    }

    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _orders.length + 1,
        itemBuilder: (context, index) {
          if (index == _orders.length) return _buildFooter();
          return _buildOrderCard(_orders[index]);
        },
      ),
    );
  }

  Widget _buildFooter() {
    if (_isLoading) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return Center(
        child: TextButton(onPressed: _loadMore, child: const Text('Retry loading history')),
      );
    }
    if (!_hasMore) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Center(child: Text('End of history', style: TextStyle(color: KdsTheme.textMuted))),
      );
    }
    return Center(
      child: TextButton.icon(
        onPressed: _loadMore,
        icon: const Icon(Icons.expand_more),
        label: const Text('Load older orders'),
      ),
    );
  }

  Widget _buildOrderCard(KitchenOrderModel order) {
    final isRejected = order.status == 'REJECTED';
    return Card(
      color: KdsTheme.surface,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: isRejected ? Colors.redAccent.withOpacity(0.5) : KdsTheme.border,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text('${order.tableDisplayName} • #${order.orderNumber}',
                      style: const TextStyle(
                          color: KdsTheme.textPrimary,
                          fontWeight: FontWeight.bold,
                          fontSize: 14)),
                ),
                _statusBadge(order.status, isRejected),
              ],
            ),
            const SizedBox(height: 8),
            ...order.items.map((item) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Text('${item.activeQuantity}x ${item.itemName} (${item.variantName})',
                      style: const TextStyle(color: KdsTheme.textSecondary, fontSize: 13)),
                )),
            if (order.rejectionReason != null) ...[
              const SizedBox(height: 6),
              Text('Rejection reason: ${order.rejectionReason}',
                  style: const TextStyle(
                      color: Colors.redAccent, fontSize: 12, fontStyle: FontStyle.italic)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _statusBadge(String status, bool isRejected) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: (isRejected ? Colors.redAccent : Colors.green).withOpacity(0.2),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(status,
            style: TextStyle(
                color: isRejected ? Colors.redAccent : Colors.greenAccent,
                fontWeight: FontWeight.bold,
                fontSize: 11)),
      );
}
