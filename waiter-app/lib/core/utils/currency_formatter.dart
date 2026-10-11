import 'package:intl/intl.dart';

class CurrencyFormatter {
  static final _formatter = NumberFormat.currency(
    locale: 'en_IN',
    symbol: '₹',
    decimalDigits: 2,
  );

  static String format(dynamic value) {
    if (value == null) return '₹0.00';
    if (value is num) {
      return _formatter.format(value);
    }
    final parsed = double.tryParse(value.toString());
    if (parsed != null) {
      return _formatter.format(parsed);
    }
    return '₹$value';
  }
}
