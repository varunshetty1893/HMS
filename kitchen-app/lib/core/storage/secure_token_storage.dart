import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureTokenStorage {
  final FlutterSecureStorage _storage;

  SecureTokenStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const String _accessTokenKey = 'kds_access_token';
  static const String _refreshTokenKey = 'kds_refresh_token';
  static const String _userRoleKey = 'kds_user_role';
  static const String _usernameKey = 'kds_username';

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
    required String role,
    required String username,
  }) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
    await _storage.write(key: _userRoleKey, value: role);
    await _storage.write(key: _usernameKey, value: username);
  }

  Future<String?> getAccessToken() => _storage.read(key: _accessTokenKey);
  Future<String?> getRefreshToken() => _storage.read(key: _refreshTokenKey);
  Future<String?> getUserRole() => _storage.read(key: _userRoleKey);
  Future<String?> getUsername() => _storage.read(key: _usernameKey);

  Future<void> clear() async {
    await _storage.deleteAll();
  }
}
