import 'package:flutter/material.dart';

class TimeFormatter {
  static String formatElapsed(DateTime? placedAt) {
    if (placedAt == null) return '00:00';
    final elapsed = DateTime.now().toUtc().difference(placedAt.toUtc());
    final minutes = elapsed.inMinutes;
    final seconds = elapsed.inSeconds % 60;
    return '${minutes.toString().padLeft(2, '0')}m ${seconds.toString().padLeft(2, '0')}s';
  }

  static Color getElapsedColor(DateTime? placedAt) {
    if (placedAt == null) return Colors.grey;
    final elapsed = DateTime.now().toUtc().difference(placedAt.toUtc());
    if (elapsed.inMinutes >= 20) {
      return const Color(0xFFEF4444); // red - critical
    } else if (elapsed.inMinutes >= 10) {
      return const Color(0xFFF59E0B); // amber - warning
    }
    return const Color(0xFF10B981); // emerald - normal
  }
}
