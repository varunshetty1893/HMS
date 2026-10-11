import 'package:intl/intl.dart';

class DateFormatter {
  static String formatTime(dynamic dateTime) {
    if (dateTime == null) return '';
    DateTime dt;
    if (dateTime is DateTime) {
      dt = dateTime;
    } else {
      dt = DateTime.tryParse(dateTime.toString()) ?? DateTime.now();
    }
    return DateFormat('hh:mm a').format(dt.toLocal());
  }

  static String formatDateTime(dynamic dateTime) {
    if (dateTime == null) return '';
    DateTime dt;
    if (dateTime is DateTime) {
      dt = dateTime;
    } else {
      dt = DateTime.tryParse(dateTime.toString()) ?? DateTime.now();
    }
    return DateFormat('dd MMM yyyy, hh:mm a').format(dt.toLocal());
  }

  static String elapsed(dynamic dateTime) {
    if (dateTime == null) return '';
    DateTime dt;
    if (dateTime is DateTime) {
      dt = dateTime;
    } else {
      dt = DateTime.tryParse(dateTime.toString()) ?? DateTime.now();
    }
    final diff = DateTime.now().toUtc().difference(dt.toUtc());
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    return '${diff.inHours}h ${diff.inMinutes % 60}m ago';
  }
}
