import 'package:flutter/foundation.dart';

/// Centralized environment and API configuration for the Kitchen Display System (KDS) app.
///
/// Supports runtime configuration via Flutter's `--dart-define`:
/// - `--dart-define=API_HOST=192.168.1.x`
/// - `--dart-define=API_PORT=8000`
/// - `--dart-define=API_BASE_URL=http://192.168.1.x:8000/api/v1`
/// - `--dart-define=WS_URL=ws://192.168.1.x:8000/api/v1/ws`
class EnvConfig {
  static const String _apiHost = String.fromEnvironment('API_HOST');
  static const String _apiPort = String.fromEnvironment('API_PORT', defaultValue: '8000');
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

  /// Resolved API Base URL.
  static String get apiBaseUrl {
    if (_rawApiBaseUrl.isNotEmpty) {
      final trimmed = _rawApiBaseUrl.trim();
      return trimmed.endsWith('/') ? trimmed.substring(0, trimmed.length - 1) : trimmed;
    }
    return 'http://$apiHost:$apiPort/api/v1';
  }

  /// Resolved WebSocket URL for real-time KDS order events.
  static String get wsUrl {
    if (_rawWsUrl.isNotEmpty) {
      final trimmed = _rawWsUrl.trim();
      return trimmed.endsWith('/') ? trimmed.substring(0, trimmed.length - 1) : trimmed;
    }
    return 'ws://$apiHost:$apiPort/api/v1/ws';
  }
}
