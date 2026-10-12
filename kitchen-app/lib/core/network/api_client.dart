import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../config/env_config.dart';
import '../storage/secure_token_storage.dart';
import 'api_exceptions.dart';
import 'auth_refresh_client.dart';

class ApiClient {
  final http.Client _httpClient;
  final SecureTokenStorage _tokenStorage;

  ApiClient({
    http.Client? httpClient,
    SecureTokenStorage? tokenStorage,
  }) : this._internal(httpClient, tokenStorage ?? SecureTokenStorage());

  ApiClient._internal(http.Client? httpClient, SecureTokenStorage storage)
      : _httpClient = httpClient ?? AuthRefreshClient(storage),
        _tokenStorage = storage;

  String get _baseUrl => EnvConfig.apiBaseUrl;

  /// Resolves the absolute [Uri] from [baseUrl] and [path], ensuring the
  /// FastAPI version prefix (`/api/v1`) is neither omitted nor duplicated.
  static Uri resolveUri(String baseUrl, String path, {Map<String, String>? queryParams}) {
    // 1. Strip trailing slashes from baseUrl
    String cleanBase = baseUrl.trim();
    while (cleanBase.endsWith('/')) {
      cleanBase = cleanBase.substring(0, cleanBase.length - 1);
    }

    // 2. Normalize path: ensure leading slash
    String cleanPath = path.trim();
    if (!cleanPath.startsWith('/')) {
      cleanPath = '/$cleanPath';
    }

    // 3. Prevent duplicate or missing /api/v1
    const v1Prefix = '/api/v1';
    final baseHasV1 = cleanBase.endsWith(v1Prefix);
    final pathHasV1 = cleanPath.startsWith('$v1Prefix/') || cleanPath == v1Prefix;

    if (baseHasV1 && pathHasV1) {
      // Both base and path contain /api/v1 -> remove from path to prevent duplication
      cleanPath = cleanPath.substring(v1Prefix.length);
    } else if (!baseHasV1 && !pathHasV1) {
      // Neither base nor path has /api/v1 -> prepend to path for FastAPI route match
      cleanPath = '$v1Prefix$cleanPath';
    }

    final fullUrl = '$cleanBase$cleanPath';
    var uri = Uri.parse(fullUrl);
    if (queryParams != null && queryParams.isNotEmpty) {
      uri = uri.replace(queryParameters: queryParams);
    }
    return uri;
  }

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
    // Route in FastAPI is /api/v1/auth/login
    final url = resolveUri(_baseUrl, '/auth/login');
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
    final queryParams = statusFilter != null ? {'status': statusFilter} : null;
    final url = resolveUri(_baseUrl, '/kitchen/orders/active', queryParams: queryParams);
    final res = await _httpClient.get(url, headers: await _headers());
    return _handleResponse(res) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> acceptOrder(String orderId, int expectedVersion) async {
    final url = resolveUri(_baseUrl, '/kitchen/orders/$orderId/accept');
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
    final url = resolveUri(_baseUrl, '/kitchen/orders/$orderId/reject');
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
    final url = resolveUri(_baseUrl, '/kitchen/orders/$orderId/preparing');
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
    final url = resolveUri(_baseUrl, '/kitchen/orders/$orderId/ready');
    final res = await _httpClient.post(
      url,
      headers: await _headers(),
      body: jsonEncode({'expected_version': expectedVersion}),
    );
    return _handleResponse(res) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> acknowledgeModifications(String orderId) async {
    final url = resolveUri(_baseUrl, '/kitchen/orders/$orderId/acknowledge-modifications');
    final res = await _httpClient.post(
      url,
      headers: await _headers(),
      body: jsonEncode({}),
    );
    return _handleResponse(res) as Map<String, dynamic>;
  }

  Future<List<dynamic>> getOrderHistory({int page = 1, int pageSize = 20}) async {
    final url = resolveUri(
      _baseUrl,
      '/kitchen/orders/history',
      queryParams: {
        'page': page.toString(),
        'page_size': pageSize.toString(),
      },
    );
    final res = await _httpClient.get(url, headers: await _headers());
    return _handleResponse(res) as List<dynamic>;
  }
}
