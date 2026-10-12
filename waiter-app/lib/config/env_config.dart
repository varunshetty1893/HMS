import 'package:flutter/foundation.dart';

/// Centralized environment and API configuration for the Waiter app.
///
/// Supports runtime configuration via Flutter's `--dart-define`:
///
/// 1. Production Release (Required):
///    `--dart-define=APP_ENV=production --dart-define=API_BASE_URL=https://hms-api.onrender.com/api/v1`
///    Enforces HTTPS and fails safely if missing.
///
/// 2. Physical Phone on LAN (Development):
///    `--dart-define=API_HOST=192.168.1.x`
///    Automatically derives:
///      - API Base URL: `http://192.168.1.x:8000/api/v1`
///      - WebSocket URL: `ws://192.168.1.x:8000/api/v1/ws`
///
/// 3. Android Emulator (Default dev):
///    Uses `10.0.2.2:8000` to reach local development workstation.
class EnvConfig {
  static const String _apiHost = String.fromEnvironment('API_HOST');
  static const String _apiPort =
      String.fromEnvironment('API_PORT', defaultValue: '8000');
  static const String _rawApiBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const String _rawWsUrl = String.fromEnvironment('WS_URL');
  static const String _allowInsecureHttp =
      String.fromEnvironment('ALLOW_INSECURE_HTTP', defaultValue: 'false');

  static const String appEnv = String.fromEnvironment(
    'APP_ENV',
    defaultValue: 'development',
  );

  /// True if running in production mode or as a compiled release binary.
  static bool get isProduction =>
      appEnv.trim().toLowerCase() == 'production' || kReleaseMode;

  /// True if running in development mode.
  static bool get isDevelopment => !isProduction;

  /// Default host when neither [API_HOST] nor [API_BASE_URL] is specified.
  /// Only permitted in development mode.
  static String get defaultHost {
    if (isProduction) {
      throw StateError(
        'Production Configuration Error: Default loopback host is not permitted in production. '
        'Provide an explicit backend URL via --dart-define=API_BASE_URL=https://...',
      );
    }
    if (kIsWeb) return '127.0.0.1';
    return '10.0.2.2';
  }

  /// Resolved host address.
  static String get apiHost {
    if (_apiHost.isNotEmpty) return _apiHost.trim();
    return defaultHost;
  }

  /// Resolved port number.
  static String get apiPort => _apiPort.trim();

  /// Resolved API Base URL (guaranteed to end with `/api/v1` without trailing slash).
  static String get apiBaseUrl {
    String resolved;
    if (_rawApiBaseUrl.isNotEmpty) {
      final trimmed = _rawApiBaseUrl.trim();
      resolved = trimmed.endsWith('/')
          ? trimmed.substring(0, trimmed.length - 1)
          : trimmed;
    } else {
      if (isProduction) {
        throw StateError(
          'Production Configuration Error: Missing API_BASE_URL. '
          'Build with --dart-define=API_BASE_URL=https://<your-backend-host>/api/v1',
        );
      }
      resolved = 'http://$apiHost:$apiPort/api/v1';
    }

    if (isProduction &&
        resolved.startsWith('http://') &&
        !resolved.contains('localhost') &&
        !resolved.contains('127.0.0.1') &&
        _allowInsecureHttp != 'true') {
      throw StateError(
        'Production Security Violation: Insecure HTTP protocol ($resolved) is forbidden. '
        'Provide an HTTPS URL or explicitly pass --dart-define=ALLOW_INSECURE_HTTP=true for private LANs.',
      );
    }

    return resolved;
  }

  /// Resolved WebSocket URL for real-time order status updates.
  static String get wsUrl {
    if (_rawWsUrl.isNotEmpty) {
      final trimmed = _rawWsUrl.trim();
      return trimmed.endsWith('/')
          ? trimmed.substring(0, trimmed.length - 1)
          : trimmed;
    }

    // Derive WebSocket URL from apiBaseUrl
    final base = apiBaseUrl;
    if (base.startsWith('https://')) {
      final withoutScheme = base.substring(8);
      return 'wss://$withoutScheme/ws';
    } else if (base.startsWith('http://')) {
      final withoutScheme = base.substring(7);
      return 'ws://$withoutScheme/ws';
    }
    return 'ws://$apiHost:$apiPort/api/v1/ws';
  }
}
