import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../config/env_config.dart';
import '../storage/secure_token_storage.dart';
import 'api_exceptions.dart';

class ApiClient {
  final http.Client _httpClient;
  final SecureTokenStorage _tokenStorage;

  ApiClient({
    http.Client? httpClient,
    SecureTokenStorage? tokenStorage,
  })  : _httpClient = httpClient ?? http.Client(),
        _tokenStorage = tokenStorage ?? SecureTokenStorage();

  String get _baseUrl => EnvConfig.apiBaseUrl;

  Future<Map<String, String>> _headers() async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    final token = await _tokenStorage.getAccessToken();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  dynamic _handleResponse(http.Response res) {
    if (res.statusCode >= 200 && res.statusCode < 300) {
      if (res.statusCode == 204 || res.body.isEmpty) return null;
      return jsonDecode(res.body);
    }

    String code = 'UNKNOWN_ERROR';
    String message = 'HTTP ${res.statusCode}';
    Map<String, dynamic>? details;

    try {
      final body = jsonDecode(res.body);
      if (body is Map<String, dynamic> && body.containsKey('error')) {
        final err = body['error'];
        code = err['code'] ?? code;
        message = err['message'] ?? message;
        details = err['details'] is Map<String, dynamic> ? err['details'] : null;
      }
    } catch (_) {}

    if (res.statusCode == 401) {
      throw AuthException(code: code, message: message);
    }
    if (res.statusCode == 409) {
      throw VersionConflictException(code: code, message: message, details: details);
    }
    if (res.statusCode == 422 && code == 'ORDER_MODIFICATIONS_UNACKNOWLEDGED') {
      throw UnacknowledgedModificationsException(details: details);
    }

    throw ApiException(
      code: code,
      message: message,
      statusCode: res.statusCode,
      details: details,
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Authentication
  // ─────────────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> loginStaff({
    required String username,
    required String password,
  }) async {
    final url = Uri.parse('$_baseUrl/auth/staff/login');
    final res = await _httpClient.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    final data = _handleResponse(res) as Map<String, dynamic>;

    final accessToken = data['access_token'] as String;
    final refreshToken = data['refresh_token'] as String;
    final user = data['user'] as Map<String, dynamic>;

    await _tokenStorage.saveTokens(
      accessToken: accessToken,
      refreshToken: refreshToken,
      role: user['role'] as String,
      username: user['username'] as String,
    );

    return data;
  }

  // ─────────────────────────────────────────────────────────────────────────
  // KDS Operations
  // ─────────────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> getActiveQueue({String? statusFilter}) async {
    final query = statusFilter != null ? '?status=$statusFilter' : '';
    final url = Uri.parse('$_baseUrl/kitchen/orders/active$query');
    final res = await _httpClient.get(url, headers: await _headers());
    return _handleResponse(res) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> acceptOrder(String orderId, int expectedVersion) async {
    final url = Uri.parse('$_baseUrl/kitchen/orders/$orderId/accept');
    final res = await _httpClient.post(
      url,
      headers: await _headers(),
      body: jsonEncode({'expected_version': expectedVersion}),
    );
    return _handleResponse(res) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> rejectOrder(
    String orderId,
    int expectedVersion,
    String reason,
  ) async {
    final url = Uri.parse('$_baseUrl/kitchen/orders/$orderId/reject');
    final res = await _httpClient.post(
      url,
      headers: await _headers(),
      body: jsonEncode({
        'expected_version': expectedVersion,
        'reason': reason,
      }),
    );
    return _handleResponse(res) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> startPreparingOrder(
    String orderId,
    int expectedVersion,
  ) async {
    final url = Uri.parse('$_baseUrl/kitchen/orders/$orderId/preparing');
    final res = await _httpClient.post(
      url,
      headers: await _headers(),
      body: jsonEncode({'expected_version': expectedVersion}),
    );
    return _handleResponse(res) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> markOrderReady(
    String orderId,
    int expectedVersion,
  ) async {
    final url = Uri.parse('$_baseUrl/kitchen/orders/$orderId/ready');
    final res = await _httpClient.post(
      url,
      headers: await _headers(),
      body: jsonEncode({'expected_version': expectedVersion}),
    );
    return _handleResponse(res) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> acknowledgeModifications(String orderId) async {
    final url = Uri.parse('$_baseUrl/kitchen/orders/$orderId/acknowledge-modifications');
    final res = await _httpClient.post(
      url,
      headers: await _headers(),
      body: jsonEncode({}),
    );
    return _handleResponse(res) as Map<String, dynamic>;
  }

  Future<List<dynamic>> getOrderHistory({int page = 1, int pageSize = 20}) async {
    final url = Uri.parse('$_baseUrl/kitchen/orders/history?page=$page&page_size=$pageSize');
    final res = await _httpClient.get(url, headers: await _headers());
    return _handleResponse(res) as List<dynamic>;
  }
}
