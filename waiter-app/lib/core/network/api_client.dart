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

  /// Resolves the absolute [Uri] from [baseUrl] and [path], ensuring the
  /// FastAPI version prefix (`/api/v1`) is neither omitted nor duplicated.
  ///
  /// Examples:
  /// - `baseUrl: 'http://192.168.1.5:8000/api/v1'`, `path: '/api/v1/auth/login'`
  ///   => `http://192.168.1.5:8000/api/v1/auth/login` (duplicate stripped)
  /// - `baseUrl: 'http://192.168.1.5:8000/api/v1'`, `path: '/auth/login'`
  ///   => `http://192.168.1.5:8000/api/v1/auth/login` (clean composition)
  /// - `baseUrl: 'http://192.168.1.5:8000'`, `path: '/api/v1/auth/login'`
  ///   => `http://192.168.1.5:8000/api/v1/auth/login` (prefix retained)
  /// - `baseUrl: 'http://192.168.1.5:8000'`, `path: '/auth/login'`
  ///   => `http://192.168.1.5:8000/api/v1/auth/login` (prefix added)
  static Uri resolveUri(String baseUrl, String path,
      {Map<String, String>? queryParams}) {
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
    final pathHasV1 =
        cleanPath.startsWith('$v1Prefix/') || cleanPath == v1Prefix;

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

  Future<Map<String, String>> _buildHeaders({
    Map<String, String>? extra,
    String? idempotencyKey,
  }) async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    final token = await _tokenStorage.getAccessToken();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    if (idempotencyKey != null && idempotencyKey.isNotEmpty) {
      headers['Idempotency-Key'] = idempotencyKey;
    }
    if (extra != null) {
      headers.addAll(extra);
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
        details =
            err['details'] is Map<String, dynamic> ? err['details'] : null;
      }
    } catch (_) {}

    if (res.statusCode == 401) {
      throw AuthException(code: code, message: message);
    }
    if (res.statusCode == 409) {
      throw ConflictException(code: code, message: message);
    }
    if (res.statusCode == 422 && code == 'LIMIT_EXCEEDED') {
      throw TableLimitExceededException(
          code: code, message: message, details: details);
    }

    throw ApiException(code: code, message: message, details: details);
  }

  Future<dynamic> get(String path, {Map<String, String>? queryParams}) async {
    final uri = resolveUri(_baseUrl, path, queryParams: queryParams);
    final headers = await _buildHeaders();
    final res = await _httpClient.get(uri, headers: headers);
    return _handleResponse(res);
  }

  /// [data] or [body] can be used interchangeably as the JSON payload.
  Future<dynamic> post(
    String path, {
    Map<String, dynamic>? data,
    Map<String, dynamic>? body,
    String? idempotencyKey,
    Map<String, String>? headers,
  }) async {
    final uri = resolveUri(_baseUrl, path);
    final payload = data ?? body;
    final builtHeaders = await _buildHeaders(
      extra: headers,
      idempotencyKey: idempotencyKey,
    );
    final res = await _httpClient.post(
      uri,
      headers: builtHeaders,
      body: payload != null ? jsonEncode(payload) : null,
    );
    return _handleResponse(res);
  }

  /// [data] or [body] can be used interchangeably as the JSON payload.
  Future<dynamic> patch(
    String path, {
    Map<String, dynamic>? data,
    Map<String, dynamic>? body,
    Map<String, String>? headers,
  }) async {
    final payload = data ?? body;
    final uri = resolveUri(_baseUrl, path);
    final builtHeaders = await _buildHeaders(extra: headers);
    final res = await _httpClient.patch(
      uri,
      headers: builtHeaders,
      body: payload != null ? jsonEncode(payload) : null,
    );
    return _handleResponse(res);
  }
}
