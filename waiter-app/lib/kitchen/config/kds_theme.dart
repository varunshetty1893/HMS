import 'package:flutter/material.dart';

class KdsTheme {
  // Backgrounds (light)
  static const Color background = Color(0xFFF8FAFC); // slate-50
  static const Color surface = Color(0xFFFFFFFF); // white
  static const Color surfaceVariant = Color(0xFFE2E8F0); // slate-200
  static const Color border = Color(0xFFCBD5E1); // slate-300

  // Semantic KDS column colors
  static const Color placedColor = Color(0xFFD95D2B); // SpiceHub Spice Orange
  static const Color acceptedColor = Color(0xFFEAB308); // yellow-500
  static const Color preparingColor = Color(0xFF3B82F6); // blue-500
  static const Color readyColor = Color(0xFF315B42); // SpiceHub Herb Green
  static const Color rejectedColor = Color(0xFFEF4444); // red-500

  // Alert colors for modifications
  static const Color alertAdd = Color(0xFF22C55E); // green
  static const Color alertCancel = Color(0xFFF43F5E); // rose

  // Typography Colors
  static const Color textPrimary = Color(0xFF0F172A);
  static const Color textSecondary = Color(0xFF475569);
  static const Color textMuted = Color(0xFF64748B);

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: background,
      primaryColor: placedColor,
      cardColor: surface,
      dividerColor: border,
      colorScheme: const ColorScheme.light(
        primary: placedColor,
        secondary: preparingColor,
        surface: surface,
        error: rejectedColor,
        onPrimary: Colors.white,
        onSurface: textPrimary,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surface,
        foregroundColor: textPrimary,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 1,
        centerTitle: false,
        iconTheme: IconThemeData(color: textPrimary),
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.bold,
          letterSpacing: 0.5,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: const Size(double.infinity, 52), // large 52dp touch target
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.bold,
          color: textPrimary,
        ),
        titleLarge: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.bold,
          color: textPrimary,
        ),
        titleMedium: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
        bodyMedium: TextStyle(
          fontSize: 14,
          color: textSecondary,
        ),
        bodySmall: TextStyle(
          fontSize: 12,
          color: textMuted,
        ),
      ),
    );
  }
}
