import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/kds_theme.dart';
import '../../models/kitchen_order_model.dart';
import '../../widgets/connection_status_banner.dart';
import '../../widgets/cancellation_alert_banner.dart';
import '../../../features/auth/auth_controller.dart';
import '../kds_history/kds_history_screen.dart';
import 'kds_controller.dart';
import 'reject_order_dialog.dart';
import 'ticket_card.dart';

class KdsBoardScreen extends ConsumerStatefulWidget {
  const KdsBoardScreen({super.key});

  @override
  ConsumerState<KdsBoardScreen> createState() => _KdsBoardScreenState();
}

class _KdsBoardScreenState extends ConsumerState<KdsBoardScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _showRejectDialog(KitchenOrderModel order) {
    showDialog(
      context: context,
      builder: (_) => RejectOrderDialog(
        orderNumber: order.orderNumber,
        onConfirm: (reason) {
          ref.read(kdsControllerProvider.notifier).rejectOrder(order, reason);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(kdsControllerProvider);
    final controller = ref.read(kdsControllerProvider.notifier);

    final placedOrders = state.orders.where((o) => o.status == 'PLACED').toList();
    final preparingOrders = state.orders.where((o) => o.status == 'ACCEPTED' || o.status == 'PREPARING').toList();
    final readyOrders = state.orders.where((o) => o.status == 'READY').toList();

    return Scaffold(
      backgroundColor: KdsTheme.background,
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.soup_kitchen, color: KdsTheme.placedColor, size: 24),
            const SizedBox(width: 10),
            const Text('KDS Board'),
            const SizedBox(width: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: state.isConnected ? Colors.green.shade900.withOpacity(0.4) : Colors.red.shade900,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: state.isConnected ? Colors.green : Colors.red),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 4,
                    backgroundColor: state.isConnected ? Colors.green : Colors.redAccent,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    state.isConnected ? 'LIVE' : 'OFFLINE',
                    style: TextStyle(
                      color: state.isConnected ? Colors.green.shade700 : KdsTheme.textSecondary,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Queue',
            onPressed: () => controller.loadQueue(),
          ),
          IconButton(
            icon: const Icon(Icons.history_rounded),
            tooltip: 'Order History',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const KdsHistoryScreen()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign Out',
            onPressed: () => ref.read(authControllerProvider.notifier).logout(),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(50),
          child: LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth >= 900) {
                // Wide tablet screen: Show column header strip instead of tabs
                return Container(
                  height: 48,
                  decoration: const BoxDecoration(
                    color: KdsTheme.surface,
                    border: Border(bottom: BorderSide(color: KdsTheme.border)),
                  ),
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    children: [
                      _buildColumnHeader('NEW ORDERS', placedOrders.length, KdsTheme.placedColor),
                      const SizedBox(width: 16),
                      _buildColumnHeader('IN PREPARATION', preparingOrders.length, KdsTheme.preparingColor),
                      const SizedBox(width: 16),
                      _buildColumnHeader('READY FOR PICKUP', readyOrders.length, KdsTheme.readyColor),
                    ],
                  ),
                );
              }
              // Narrow phone screen: show standard tab bar
              return TabBar(
                controller: _tabController,
                indicatorColor: KdsTheme.placedColor,
                tabs: [
                  Tab(text: 'New (${placedOrders.length})'),
                  Tab(text: 'Prep (${preparingOrders.length})'),
                  Tab(text: 'Ready (${readyOrders.length})'),
                ],
              );
            },
          ),
        ),
      ),
      body: Column(
        children: [
          ConnectionStatusBanner(isConnected: state.isConnected),
          if (state.errorMessage != null)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.shade900.withOpacity(0.35),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.redAccent),
              ),
              child: Text(
                'Could not update the order: ${state.errorMessage}. Tap acknowledge to retry.',
                style: const TextStyle(color: Colors.white, fontSize: 13),
              ),
            ),
          CancellationAlertBanner(
            alerts: state.cancellations,
            onDismiss: controller.dismissCancellation,
          ),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) {
                if (constraints.maxWidth >= 900) {
                  // Tablet multi-column layout
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: _buildTicketList(placedOrders, 'No new orders', state.acknowledgingOrderIds),
                      ),
                      const VerticalDivider(width: 1, color: KdsTheme.border),
                      Expanded(
                        child: _buildTicketList(preparingOrders, 'No orders in prep', state.acknowledgingOrderIds),
                      ),
                      const VerticalDivider(width: 1, color: KdsTheme.border),
                      Expanded(
                        child: _buildTicketList(readyOrders, 'No orders ready', state.acknowledgingOrderIds),
                      ),
                    ],
                  );
                }

                // Phone TabBarView layout
                return TabBarView(
                  controller: _tabController,
                  children: [
                    _buildTicketList(placedOrders, 'No new orders', state.acknowledgingOrderIds),
                    _buildTicketList(preparingOrders, 'No orders in prep', state.acknowledgingOrderIds),
                    _buildTicketList(readyOrders, 'No orders ready', state.acknowledgingOrderIds),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildColumnHeader(String title, int count, Color color) {
    return Expanded(
      child: Row(
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: KdsTheme.textPrimary,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              '$count',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTicketList(
    List<KitchenOrderModel> list,
    String emptyMessage,
    Set<String> acknowledgingOrderIds,
  ) {
    if (list.isEmpty) {
      return Center(
        child: Text(
          emptyMessage,
          style: const TextStyle(color: KdsTheme.textMuted, fontSize: 14),
        ),
      );
    }

    final controller = ref.read(kdsControllerProvider.notifier);

    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: list.length,
      itemBuilder: (context, index) {
        final order = list[index];
        return TicketCard(
          order: order,
          onAccept: () => controller.acceptOrder(order),
          onReject: () => _showRejectDialog(order),
          onStartPreparing: () => controller.startPreparingOrder(order),
          onMarkReady: () => controller.markOrderReady(order),
          onAcknowledgeModifications: () => controller.acknowledgeModifications(order),
          isAcknowledgingModifications: acknowledgingOrderIds.contains(order.id),
        );
      },
    );
  }
}
