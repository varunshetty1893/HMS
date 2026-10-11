import 'package:flutter/material.dart';

class WaiterTheme {
  static const Color background = Color(0xFF0F172A); // Slate 900
  static const Color surface = Color(0xFF1E293B); // Slate 800
  static const Color surfaceVariant = Color(0xFF334155); // Slate 700
  static const Color surfaceLight = Color(0xFF475569); // Slate 600

  static const Color primary = Color(0xFFF59E0B); // Amber 500
  static const Color primaryDark = Color(0xFFD97706); // Amber 600
  static const Color primaryLight = Color(0xFFFDE68A); // Amber 200

  static const Color availableGreen = Color(0xFF10B981); // Emerald 500
  static const Color availableGreenBg = Color(0xFF064E3B); // Emerald 900
  static const Color occupiedBlue = Color(0xFF3B82F6); // Blue 500
  static const Color occupiedBlueBg = Color(0xFF1E3A8A); // Blue 900
  static const Color readyAmber = Color(0xFFF59E0B); // Amber 500
  static const Color readyAmberBg = Color(0xFF78350F); // Amber 900
  static const Color errorRed = Color(0xFFEF4444); // Red 500
  static const Color errorRedBg = Color(0xFF7F1D1D); // Red 900

  static const Color textPrimary = Color(0xFFF8FAFC); // Slate 50
  static const Color textSecondary = Color(0xFFCBD5E1); // Slate 300
  static const Color textMuted = Color(0xFF94A3B8); // Slate 400

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        secondary: primaryDark,
        surface: surface,
        error: errorRed,
        onPrimary: Colors.black,
        onSecondary: Colors.black,
        onSurface: textPrimary,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surface,
        elevation: 0,
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
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: surfaceVariant, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceVariant,
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
          foregroundColor: Colors.black,
          elevation: 0,
          padding:
              const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
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
  static const Color errorColor = WaiterTheme.errorRed;

  // Text
  static const Color textPrimary = WaiterTheme.textPrimary;
  static const Color textSecondary = WaiterTheme.textSecondary;
  static const Color textMuted = WaiterTheme.textMuted;

  static ThemeData get darkTheme => WaiterTheme.darkTheme;
}
