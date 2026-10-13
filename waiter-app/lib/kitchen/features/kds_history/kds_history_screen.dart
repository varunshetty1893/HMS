import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/kds_theme.dart';
import '../../data/kitchen_api.dart';
import '../../models/kitchen_order_model.dart';

final kdsHistoryProvider = FutureProvider.autoDispose<List<KitchenOrderModel>>((ref) async {
  final apiClient = ref.read(kitchenApiProvider);
  final data = await apiClient.getOrderHistory(page: 1, pageSize: 30);
  return data
      .map((e) => KitchenOrderModel.fromJson(e as Map<String, dynamic>))
      .toList();
});

class KdsHistoryScreen extends ConsumerWidget {
  const KdsHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final historyAsync = ref.watch(kdsHistoryProvider);

    return Scaffold(
      backgroundColor: KdsTheme.background,
      appBar: AppBar(
        title: const Text('Kitchen Order History'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.refresh(kdsHistoryProvider),
          ),
        ],
      ),
      body: historyAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Text('Failed to load history: $err', style: const TextStyle(color: Colors.redAccent)),
        ),
        data: (orders) {
          if (orders.isEmpty) {
            return const Center(
              child: Text('No past orders in history', style: TextStyle(color: KdsTheme.textMuted)),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: orders.length,
            itemBuilder: (context, index) {
              final order = orders[index];
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
                          Text(
                            '${order.tableDisplayName} • #${order.orderNumber}',
                            style: const TextStyle(
                              color: KdsTheme.textPrimary,
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: isRejected
                                  ? Colors.redAccent.withOpacity(0.2)
                                  : Colors.green.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              order.status,
                              style: TextStyle(
                                color: isRejected ? Colors.redAccent : Colors.greenAccent,
                                fontWeight: FontWeight.bold,
                                fontSize: 11,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      ...order.items.map((it) {
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 2),
                          child: Text(
                            '${it.activeQuantity}x ${it.itemName} (${it.variantName})',
                            style: const TextStyle(color: KdsTheme.textSecondary, fontSize: 13),
                          ),
                        );
                      }),
                      if (order.rejectionReason != null) ...[
                        const SizedBox(height: 6),
                        Text(
                          'Rejection Reason: ${order.rejectionReason}',
                          style: const TextStyle(color: Colors.redAccent, fontSize: 12, fontStyle: FontStyle.italic),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
