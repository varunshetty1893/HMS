import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../widgets/connection_banner.dart';
import '../auth/auth_controller.dart';
import '../order_confirmation/order_confirmation_controller.dart';
import '../order_confirmation/order_confirmation_screen.dart';
import '../pickup_queue/pickup_queue_screen.dart';
import '../table_detail/table_detail_screen.dart';
import 'floor_grid_controller.dart';
import 'table_card.dart';

class FloorTablesScreen extends ConsumerWidget {
  const FloorTablesScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(floorGridControllerProvider);
    final controller = ref.read(floorGridControllerProvider.notifier);
    final authState = ref.watch(authControllerProvider);
    final confirmations = ref.watch(orderConfirmationControllerProvider);

    // New QR order request: alert the waiter even when this screen is in front.
    ref.listen<OrderConfirmationState>(orderConfirmationControllerProvider,
        (previous, next) {
      if (next.count < (previous?.count ?? 0) || next.count == 0) {
        ScaffoldMessenger.of(context).hideCurrentSnackBar();
      }
      if (next.count > (previous?.count ?? 0)) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(
            SnackBar(
              duration: const Duration(seconds: 8),
              content: Text(
                '${next.items.last.tableLabel} wants to order. Confirm guests are seated?',
              ),
              action: SnackBarAction(
                label: 'REVIEW',
                onPressed: () {
                  ScaffoldMessenger.of(context).hideCurrentSnackBar();
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => const OrderConfirmationScreen(),
                    ),
                  );
                },
              ),
            ),
          );
      }
    });

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Restaurant Floor',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
            ),
            if (authState.user != null)
              Text(
                'Waiter: ${authState.user!.fullName}',
                style: const TextStyle(
                  fontSize: 12,
                  color: AppTheme.textSecondary,
                  fontWeight: FontWeight.normal,
                ),
              ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Floor',
            onPressed: () => controller.loadTables(),
          ),
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.how_to_reg),
                tooltip: 'Order Requests',
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => const OrderConfirmationScreen(),
                    ),
                  );
                },
              ),
              if (confirmations.count > 0)
                Positioned(
                  top: 8,
                  right: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: AppTheme.errorColor,
                      shape: BoxShape.circle,
                    ),
                    constraints: const BoxConstraints(
                      minWidth: 16,
                      minHeight: 16,
                    ),
                    child: Text(
                      '${confirmations.count}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
            ],
          ),
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.room_service),
                tooltip: 'Pickup Queue',
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => const PickupQueueScreen(),
                    ),
                  );
                },
              ),
              if (state.totalReadyOrders > 0)
                Positioned(
                  top: 8,
                  right: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: AppTheme.readyColor,
                      shape: BoxShape.circle,
                    ),
                    constraints: const BoxConstraints(
                      minWidth: 16,
                      minHeight: 16,
                    ),
                    child: Text(
                      '${state.totalReadyOrders}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Logout',
            onPressed: () => ref.read(authControllerProvider.notifier).logout(),
          ),
        ],
      ),
      body: Column(
        children: [
          const ConnectionBanner(),
          if (confirmations.count > 0)
            Material(
              color: WaiterTheme.readyAmberBg,
              child: InkWell(
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => const OrderConfirmationScreen(),
                    ),
                  );
                },
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  child: Row(
                    children: [
                      const Icon(Icons.notifications_active,
                          color: AppTheme.warningColor),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          confirmations.count == 1
                              ? '1 table is waiting for you to confirm its order'
                              : '${confirmations.count} tables are waiting for you to confirm their orders',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    onChanged: controller.setSearchQuery,
                    decoration: InputDecoration(
                      hintText: 'Search table number or section...',
                      prefixIcon: const Icon(Icons.search, size: 20),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 12),
                      filled: true,
                      fillColor: AppTheme.cardColor,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide:
                            const BorderSide(color: AppTheme.borderColor),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide:
                            const BorderSide(color: AppTheme.borderColor),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Row(
              children: [
                _buildFilterChip(
                  context,
                  label: 'All (${state.tables.length})',
                  filterKey: 'ALL',
                  isSelected: state.selectedFilter == 'ALL',
                  onSelected: () => controller.setFilter('ALL'),
                ),
                const SizedBox(width: 8),
                _buildFilterChip(
                  context,
                  label:
                      'Occupied (${state.tables.where((t) => t.isOccupied).length})',
                  filterKey: 'OCCUPIED',
                  isSelected: state.selectedFilter == 'OCCUPIED',
                  onSelected: () => controller.setFilter('OCCUPIED'),
                ),
                const SizedBox(width: 8),
                _buildFilterChip(
                  context,
                  label:
                      'Available (${state.tables.where((t) => t.isAvailable).length})',
                  filterKey: 'AVAILABLE',
                  isSelected: state.selectedFilter == 'AVAILABLE',
                  onSelected: () => controller.setFilter('AVAILABLE'),
                ),
                const SizedBox(width: 8),
                _buildFilterChip(
                  context,
                  label: 'Ready Food (${state.totalReadyOrders})',
                  filterKey: 'READY',
                  isSelected: state.selectedFilter == 'READY',
                  badgeColor: AppTheme.readyColor,
                  onSelected: () => controller.setFilter('READY'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: state.isLoading
                ? const Center(child: CircularProgressIndicator())
                : state.error != null
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              state.error!,
                              style:
                                  const TextStyle(color: AppTheme.errorColor),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 12),
                            ElevatedButton(
                              onPressed: () => controller.loadTables(),
                              child: const Text('Retry'),
                            ),
                          ],
                        ),
                      )
                    : state.filteredTables.isEmpty
                        ? const Center(
                            child: Text(
                              'No tables found',
                              style: TextStyle(color: AppTheme.textSecondary),
                            ),
                          )
                        : RefreshIndicator(
                            onRefresh: () => controller.loadTables(),
                            child: GridView.builder(
                              padding: const EdgeInsets.all(16),
                              gridDelegate:
                                  const SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: 2,
                                childAspectRatio: 1.05,
                                crossAxisSpacing: 12,
                                mainAxisSpacing: 12,
                              ),
                              itemCount: state.filteredTables.length,
                              itemBuilder: (context, index) {
                                final table = state.filteredTables[index];
                                return TableCard(
                                  table: table,
                                  onTap: () {
                                    Navigator.of(context).push(
                                      MaterialPageRoute(
                                        builder: (_) => TableDetailScreen(
                                          table: table,
                                        ),
                                      ),
                                    );
                                  },
                                );
                              },
                            ),
                          ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(
    BuildContext context, {
    required String label,
    required String filterKey,
    required bool isSelected,
    required VoidCallback onSelected,
    Color? badgeColor,
  }) {
    return ChoiceChip(
      label: Text(
        label,
        style: TextStyle(
          color:
              isSelected ? Colors.white : badgeColor ?? AppTheme.textSecondary,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
          fontSize: 12,
        ),
      ),
      selected: isSelected,
      selectedColor: badgeColor ?? AppTheme.accentColor,
      backgroundColor: AppTheme.cardColor,
      onSelected: (_) => onSelected(),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(
          color: isSelected
              ? (badgeColor ?? AppTheme.accentColor)
              : AppTheme.borderColor,
        ),
      ),
    );
  }
}
