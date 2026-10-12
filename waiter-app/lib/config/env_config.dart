import 'package:flutter/foundation.dart';

/// Centralized environment and API configuration for the Waiter app.
///
/// Supports runtime configuration via Flutter's `--dart-define`:
///
/// 1. Physical Phone on LAN (Recommended):
///    `--dart-define=API_HOST=192.168.1.x`
///    Automatically derives:
///      - API Base URL: `http://192.168.1.x:8000/api/v1`
///      - WebSocket URL: `ws://192.168.1.x:8000/api/v1/ws`
///
/// 2. Custom Port:
///    `--dart-define=API_HOST=192.168.1.x --dart-define=API_PORT=8080`
///
/// 3. Direct Full URL Override:
///    `--dart-define=API_BASE_URL=http://192.168.1.x:8000/api/v1`
///    `--dart-define=WS_URL=ws://192.168.1.x:8000/api/v1/ws`
///
/// 4. Android Emulator (Default when no flags passed):
///    Uses `10.0.2.2:8000` to reach the development workstation loopback.
///
/// 5. Flutter Web (Default when running on web):
///    Uses `127.0.0.1:8000`.
class EnvConfig {
  static const String _apiHost = String.fromEnvironment('API_HOST');
<<<<<<< HEAD
  static const String _apiPort =
      String.fromEnvironment('API_PORT', defaultValue: '8000');
=======
  static const String _apiPort = String.fromEnvironment('API_PORT', defaultValue: '8000');
>>>>>>> 6ad4aadb1bcc2205233719a435fa8b3dbdfeb90b
  static const String _rawApiBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const String _rawWsUrl = String.fromEnvironment('WS_URL');

  static const String appEnv = String.fromEnvironment(
    'APP_ENV',
    defaultValue: 'development',
  );

  /// Default host when neither [API_HOST] nor [API_BASE_URL] is specified.
  /// - Web / desktop targets: 127.0.0.1
  /// - Mobile / Android emulator: 10.0.2.2
  static String get defaultHost {
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
    if (_rawApiBaseUrl.isNotEmpty) {
      final trimmed = _rawApiBaseUrl.trim();
<<<<<<< HEAD
      return trimmed.endsWith('/')
          ? trimmed.substring(0, trimmed.length - 1)
          : trimmed;
=======
      return trimmed.endsWith('/') ? trimmed.substring(0, trimmed.length - 1) : trimmed;
>>>>>>> 6ad4aadb1bcc2205233719a435fa8b3dbdfeb90b
    }
    return 'http://$apiHost:$apiPort/api/v1';
  }

  /// Resolved WebSocket URL for real-time order status updates.
  static String get wsUrl {
    if (_rawWsUrl.isNotEmpty) {
      final trimmed = _rawWsUrl.trim();
<<<<<<< HEAD
      return trimmed.endsWith('/')
          ? trimmed.substring(0, trimmed.length - 1)
          : trimmed;
=======
      return trimmed.endsWith('/') ? trimmed.substring(0, trimmed.length - 1) : trimmed;
>>>>>>> 6ad4aadb1bcc2205233719a435fa8b3dbdfeb90b
    }
    return 'ws://$apiHost:$apiPort/api/v1/ws';
  }
}
