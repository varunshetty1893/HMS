import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../config/env_config.dart';
import '../auth/session_events.dart';
import '../storage/secure_token_storage.dart';

/// HTTP client that transparently renews an expired access token.
///
/// When a request comes back `401`, the stored refresh token is exchanged for a
/// new access/refresh pair (`POST /auth/refresh`) and the original request is
/// replayed once with the fresh token. Concurrent 401s share a single refresh
/// because refresh tokens rotate and can only be used once.
class AuthRefreshClient extends http.BaseClient {
  AuthRefreshClient(this._storage, {http.Client? inner})
      : _inner = inner ?? http.Client();

  final http.Client _inner;
  final SecureTokenStorage _storage;
  Future<bool>? _refreshing;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    // Buffer the body so the request can be replayed after a refresh.
    final bodyBytes = await request.finalize().toBytes();
    final first = await _inner.send(_copy(request, bodyBytes));

    if (first.statusCode != 401 || _isAuthPath(request.url)) return first;

    final refreshed =
        await (_refreshing ??= _refresh().whenComplete(() => _refreshing = null));
    if (!refreshed) return first;

    await first.stream.drain<void>();
    final token = await _storage.getAccessToken();
    return _inner.send(_copy(request, bodyBytes, token: token));
  }

  bool _isAuthPath(Uri url) =>
      url.path.endsWith('/auth/login') ||
      url.path.endsWith('/auth/refresh') ||
      url.path.endsWith('/auth/logout');

  http.Request _copy(http.BaseRequest r, List<int> body, {String? token}) {
    final req = http.Request(r.method, r.url)
      ..followRedirects = r.followRedirects
      ..maxRedirects = r.maxRedirects
      ..persistentConnection = r.persistentConnection
      ..headers.addAll(r.headers)
      ..bodyBytes = body;
    if (token != null && token.isNotEmpty) {
      req.headers['Authorization'] = 'Bearer $token';
    }
    return req;
  }

  Future<bool> _refresh() async {
    try {
      final refreshToken = await _storage.getRefreshToken();
      if (refreshToken == null || refreshToken.isEmpty) {
        SessionEvents.notifyExpired();
        return false;
      }

      var base = EnvConfig.apiBaseUrl.trim();
      while (base.endsWith('/')) {
        base = base.substring(0, base.length - 1);
      }
      final prefix = base.endsWith('/api/v1') ? '' : '/api/v1';
      final uri = Uri.parse('$base$prefix/auth/refresh');

      final res = await _inner
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'refresh_token': refreshToken}),
          )
          .timeout(const Duration(seconds: 15));
      if (res.statusCode != 200) {
        // The backend explicitly rejected the refresh token -> session is over.
        // Transient failures (5xx, 429, network) must NOT log the user out.
        if (res.statusCode == 400 ||
            res.statusCode == 401 ||
            res.statusCode == 403) {
          SessionEvents.notifyExpired();
        }
        return false;
      }

      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final access = data['access_token']?.toString() ?? '';
      final refresh = data['refresh_token']?.toString() ?? '';
      if (access.isEmpty || refresh.isEmpty) return false;

      await _storage.updateTokens(accessToken: access, refreshToken: refresh);
      return true;
    } catch (_) {
      return false;
    }
  }
}
