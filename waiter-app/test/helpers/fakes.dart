import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:waiter_app/core/realtime/ws_client.dart';
import 'package:waiter_app/core/storage/secure_token_storage.dart';

/// In-memory replacement for the platform-backed secure storage.
class InMemoryTokenStorage extends SecureTokenStorage {
  final Map<String, String> data = {};

  @override
  Future<void> saveAuth({
    required String accessToken,
    required String userId,
    required String username,
    required String fullName,
    required String role,
    String? refreshToken,
  }) async {
    data['access'] = accessToken;
    if (refreshToken != null && refreshToken.isNotEmpty) {
      data['refresh'] = refreshToken;
    }
    data['userId'] = userId;
    data['username'] = username;
    data['fullName'] = fullName;
    data['role'] = role;
  }

  @override
  Future<void> updateTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    data['access'] = accessToken;
    data['refresh'] = refreshToken;
  }

  @override
  Future<String?> getAccessToken() async => data['access'];
  @override
  Future<String?> getRefreshToken() async => data['refresh'];
  @override
  Future<String?> getUserId() async => data['userId'];
  @override
  Future<String?> getUsername() async => data['username'];
  @override
  Future<String?> getFullName() async => data['fullName'];
  @override
  Future<String?> getRole() async => data['role'];

  @override
  Future<void> clearAuth() async => data.clear();
}

/// Records connect/disconnect instead of opening a real socket.
class FakeWsClient extends WaiterWebSocketClient {
  final List<String> connectedWith = [];
  int disconnectCount = 0;

  @override
  void connect(String token) => connectedWith.add(token);

  @override
  void disconnect() => disconnectCount++;
}

http.Response jsonResponse(Object body, int status) => http.Response(
      jsonEncode(body),
      status,
      headers: {'content-type': 'application/json'},
    );

Map<String, dynamic> loginBody(String role) => {
      'access_token': 'access_1',
      'refresh_token': 'refresh_1',
      'user': {
        'id': 'u-1',
        'username': 'staff1',
        'full_name': 'Staff One',
        'role': role,
      },
    };

Map<String, dynamic> meBody(String role) => {
      'id': 'u-1',
      'username': 'staff1',
      'full_name': 'Staff One',
      'role': role,
      'status': 'ACTIVE',
      'permissions': <String>[],
    };
