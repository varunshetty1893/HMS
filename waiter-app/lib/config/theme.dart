import 'package:flutter/material.dart';

class WaiterTheme {
  static const Color background = Color(0xFFF8FAFC);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surfaceVariant = Color(0xFFE2E8F0);
  static const Color surfaceLight = Color(0xFFCBD5E1);

  static const Color primary = Color(0xFFD95D2B);
  static const Color primaryDark = Color(0xFFC84E1D);
  static const Color primaryLight = Color(0xFFFED7AA);

  static const Color availableGreen = Color(0xFF15803D);
  static const Color availableGreenBg = Color(0xFFDCFCE7);
  static const Color occupiedBlue = Color(0xFF1D4ED8);
  static const Color occupiedBlueBg = Color(0xFFDBEAFE);
  static const Color readyAmber = Color(0xFFC2410C);
  static const Color readyAmberBg = Color(0xFFFFEDD5);
  static const Color errorRed = Color(0xFFB91C1C);
  static const Color errorRedBg = Color(0xFFFEE2E2);

  static const Color textPrimary = Color(0xFF0F172A);
  static const Color textSecondary = Color(0xFF475569);
  static const Color textMuted = Color(0xFF64748B);

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.light(
        primary: primary,
        secondary: primaryDark,
        surface: surface,
        error: errorRed,
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: textPrimary,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surface,
        foregroundColor: textPrimary,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 1,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
        ),
        iconTheme: IconThemeData(color: textPrimary),
      ),
      cardTheme: CardTheme(
        color: surface,
        surfaceTintColor: Colors.transparent,
        elevation: 1,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: surfaceVariant, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Color(0xFFF1F5F9),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        hintStyle: const TextStyle(color: textMuted, fontSize: 15),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.2,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: textPrimary,
          side: const BorderSide(color: surfaceVariant, width: 1.5),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      dividerColor: surfaceVariant,
    );
  }
}

/// AppTheme is a canonical alias for WaiterTheme with extra named constants
/// aligned with the screen code style.
class AppTheme {
  // Backgrounds
  static const Color backgroundColor = WaiterTheme.background;
  static const Color surfaceColor = WaiterTheme.surface;
  static const Color cardColor = WaiterTheme.surface;
  static const Color cardAltColor = WaiterTheme.surfaceVariant;
  static const Color borderColor = WaiterTheme.surfaceVariant;

  // Accent / Brand
  static const Color accentColor = WaiterTheme.primary;
  static const Color primaryColor = WaiterTheme.primary;

  // Status colours
  static const Color successColor = WaiterTheme.availableGreen;
  static const Color readyColor = WaiterTheme.readyAmber;
  static const Color warningColor = WaiterTheme.readyAmber;
  static const Color errorColor = WaiterTheme.errorRed;

  // Text
  static const Color textPrimary = WaiterTheme.textPrimary;
  static const Color textSecondary = WaiterTheme.textSecondary;
  static const Color textMuted = WaiterTheme.textMuted;

  static ThemeData get lightTheme => WaiterTheme.lightTheme;
}
