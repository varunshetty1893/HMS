import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../core/utils/currency_formatter.dart';
import '../../models/table_model.dart';
import 'order_entry_controller.dart';
import 'waiter_cart_sheet.dart';

class ManualOrderEntryScreen extends ConsumerStatefulWidget {
  final TableModel table;
  final double remainingLimit;

  const ManualOrderEntryScreen({
    Key? key,
    required this.table,
    required this.remainingLimit,
  }) : super(key: key);

  @override
  ConsumerState<ManualOrderEntryScreen> createState() =>
      _ManualOrderEntryScreenState();
}

class _ManualOrderEntryScreenState
    extends ConsumerState<ManualOrderEntryScreen> {
  final _searchController = TextEditingController();
  final _searchFocusNode = FocusNode();

  @override
  void dispose() {
    _searchController.dispose();
    _searchFocusNode.dispose();
    super.dispose();
  }

  void _openCart() async {
    final result = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => WaiterCartSheet(
        table: widget.table,
        remainingLimit: widget.remainingLimit,
      ),
    );
    if (result == true && mounted) {
      Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(orderEntryControllerProvider);
    final controller = ref.read(orderEntryControllerProvider.notifier);

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Take Order',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            Text(
              'Table ${widget.table.tableNumber}${widget.table.displayName != null ? " • ${widget.table.displayName}" : ""}',
              style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              focusNode: _searchFocusNode,
              autofocus: true,
              onChanged: (v) => controller.search(v),
              decoration: InputDecoration(
                hintText: 'Search by name or short-code (e.g. CB-H)...',
                prefixIcon:
                    const Icon(Icons.search, color: AppTheme.textSecondary),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear,
                            color: AppTheme.textSecondary),
                        onPressed: () {
                          _searchController.clear();
                          controller.search('');
                        },
                      )
                    : null,
                filled: true,
                fillColor: AppTheme.cardColor,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: AppTheme.borderColor),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: AppTheme.borderColor),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide:
                      const BorderSide(color: AppTheme.accentColor, width: 2),
                ),
              ),
            ),
          ),
          // Remaining limit info
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                const Icon(Icons.account_balance_wallet,
                    size: 14, color: AppTheme.textSecondary),
                const SizedBox(width: 4),
                Text(
                  'Remaining limit: ${CurrencyFormatter.format(widget.remainingLimit)}',
                  style: const TextStyle(
                      color: AppTheme.textSecondary, fontSize: 12),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          // Search results / hints
          Expanded(
            child: state.isSearching
                ? const Center(child: CircularProgressIndicator())
                : state.searchError != null
                    ? Center(
                        child: Text(state.searchError!,
                            style:
                                const TextStyle(color: AppTheme.errorColor)))
                    : state.searchQuery.isEmpty
                        ? _buildSearchHint()
                        : state.searchResults.isEmpty
                            ? const Center(
                                child: Text(
                                  'No items found.\nTry a different name or short-code.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(color: AppTheme.textSecondary),
                                ),
                              )
                            : _buildSearchResults(state, controller),
          ),
        ],
      ),
      // Cart FAB
      floatingActionButton: state.cartItemCount > 0
          ? FloatingActionButton.extended(
              onPressed: _openCart,
              backgroundColor: AppTheme.accentColor,
              foregroundColor: Colors.black,
              icon: const Icon(Icons.shopping_cart),
              label: Text(
                '${state.cartItemCount} items • ${CurrencyFormatter.format(state.cartTotal)}',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            )
          : null,
    );
  }

  Widget _buildSearchHint() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.restaurant_menu,
                size: 64, color: AppTheme.textMuted),
            const SizedBox(height: 16),
            const Text(
              'Search the menu',
              style: TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Type a dish name or use the short-code format.\nExample: "CB-H" for Chicken Biryani Half.',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: AppTheme.cardColor,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.borderColor),
              ),
              child: const Text(
                'Tip: Short-codes match faster (e.g. PZ-M = Pizza Medium)',
                style: TextStyle(color: AppTheme.accentColor, fontSize: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchResults(
      OrderEntryState state, OrderEntryController controller) {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      itemCount: state.searchResults.length,
      itemBuilder: (context, index) {
        final item = state.searchResults[index];
        return _buildMenuItemCard(item, controller);
      },
    );
  }

  Widget _buildMenuItemCard(
      dynamic item, OrderEntryController controller) {
    final menuItem = item as dynamic;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Item header
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppTheme.accentColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                        color: AppTheme.accentColor.withOpacity(0.4)),
                  ),
                  child: Text(
                    menuItem.shortCode ?? '',
                    style: const TextStyle(
                        color: AppTheme.accentColor,
                        fontSize: 11,
                        fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        menuItem.name,
                        style: const TextStyle(
                            color: AppTheme.textPrimary,
                            fontWeight: FontWeight.bold,
                            fontSize: 15),
                      ),
                      if (menuItem.categoryName != null)
                        Text(
                          menuItem.categoryName,
                          style: const TextStyle(
                              color: AppTheme.textSecondary, fontSize: 12),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          // Variants as pills
          if (menuItem.variants != null && menuItem.variants.isNotEmpty)
            Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Wrap(
                spacing: 8,
                runSpacing: 6,
                children: (menuItem.variants as List).map((v) {
                  final variant = v as dynamic;
                  return _buildVariantPill(menuItem, variant, controller);
                }).toList(),
              ),
            ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }

  Widget _buildVariantPill(
      dynamic item, dynamic variant, OrderEntryController controller) {
    final state = ref.watch(orderEntryControllerProvider);
    final key = '${item.id}__${variant.id}';
    final inCart = state.cart.containsKey(key);
    final cartQty = inCart ? state.cart[key]!.quantity : 0;

    return GestureDetector(
      onTap: () => controller.addToCart(item, variant),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: inCart
              ? AppTheme.accentColor.withOpacity(0.15)
              : AppTheme.cardAltColor,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: inCart ? AppTheme.accentColor : AppTheme.borderColor,
            width: inCart ? 1.5 : 1.0,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              variant.name ?? 'Regular',
              style: TextStyle(
                color: inCart ? AppTheme.accentColor : AppTheme.textPrimary,
                fontSize: 13,
                fontWeight: inCart ? FontWeight.bold : FontWeight.normal,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              CurrencyFormatter.format(variant.price as double),
              style: TextStyle(
                color: inCart ? AppTheme.accentColor : AppTheme.textSecondary,
                fontSize: 12,
              ),
            ),
            if (inCart) ...[
              const SizedBox(width: 4),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppTheme.accentColor,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '$cartQty',
                  style: const TextStyle(
                      color: Colors.black,
                      fontSize: 11,
                      fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
