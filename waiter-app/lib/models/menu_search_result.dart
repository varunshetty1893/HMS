/// Variant option returned by menu search — used in order entry.
class MenuVariantResult {
  final String id;
  final String? name;
  final double price;
  final String? variantCode;
  final String? unit;

  const MenuVariantResult({
    required this.id,
    this.name,
    required this.price,
    this.variantCode,
    this.unit,
  });

  factory MenuVariantResult.fromJson(Map<String, dynamic> json) {
    return MenuVariantResult(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ??
          json['variant_name']?.toString(),
      price: double.tryParse(json['price']?.toString() ?? '0') ?? 0.0,
      variantCode: json['variant_code']?.toString() ??
          json['code']?.toString(),
      unit: json['unit']?.toString(),
    );
  }
}

/// Menu item result from search endpoint — used in order entry.
class MenuItemResult {
  final String id;
  final String name;
  final String? shortCode;
  final String? categoryName;
  final List<MenuVariantResult> variants;

  const MenuItemResult({
    required this.id,
    required this.name,
    this.shortCode,
    this.categoryName,
    required this.variants,
  });

  factory MenuItemResult.fromJson(Map<String, dynamic> json) {
    final rawVariants = json['variants'] as List<dynamic>? ?? [];
    final variantsList = rawVariants
        .map((e) => MenuVariantResult.fromJson(e as Map<String, dynamic>))
        .toList();

    return MenuItemResult(
      id: json['id']?.toString() ?? json['item_id']?.toString() ?? '',
      name: json['name']?.toString() ??
          json['item_name']?.toString() ?? '',
      shortCode: json['short_code']?.toString() ??
          json['item_code']?.toString(),
      categoryName: json['category_name']?.toString(),
      variants: variantsList,
    );
  }
}
