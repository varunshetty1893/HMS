import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Single token store shared by the Waiter and Kitchen areas of the staff app.
class SecureTokenStorage {
  static const _keyAccessToken = 'staff_access_token';
  static const _keyRefreshToken = 'staff_refresh_token';
  static const _keyUserId = 'staff_user_id';
  static const _keyUsername = 'staff_username';
  static const _keyUserFullName = 'staff_full_name';
  static const _keyUserRole = 'staff_user_role';

  final FlutterSecureStorage _storage;

  SecureTokenStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  Future<void> saveAuth({
    required String accessToken,
    required String userId,
    required String username,
    required String fullName,
    required String role,
    String? refreshToken,
  }) async {
    await _storage.write(key: _keyAccessToken, value: accessToken);
    if (refreshToken != null && refreshToken.isNotEmpty) {
      await _storage.write(key: _keyRefreshToken, value: refreshToken);
    }
    await _storage.write(key: _keyUserId, value: userId);
    await _storage.write(key: _keyUsername, value: username);
    await _storage.write(key: _keyUserFullName, value: fullName);
    await _storage.write(key: _keyUserRole, value: role);
  }

  Future<void> updateTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(key: _keyAccessToken, value: accessToken);
    await _storage.write(key: _keyRefreshToken, value: refreshToken);
  }

  Future<String?> getAccessToken() => _storage.read(key: _keyAccessToken);
  Future<String?> getRefreshToken() => _storage.read(key: _keyRefreshToken);
  Future<String?> getUserId() => _storage.read(key: _keyUserId);
  Future<String?> getUsername() => _storage.read(key: _keyUsername);
  Future<String?> getFullName() => _storage.read(key: _keyUserFullName);
  Future<String?> getRole() => _storage.read(key: _keyUserRole);

  Future<void> clearAuth() async {
    await _storage.delete(key: _keyAccessToken);
    await _storage.delete(key: _keyRefreshToken);
    await _storage.delete(key: _keyUserId);
    await _storage.delete(key: _keyUsername);
    await _storage.delete(key: _keyUserFullName);
    await _storage.delete(key: _keyUserRole);
  }
}
