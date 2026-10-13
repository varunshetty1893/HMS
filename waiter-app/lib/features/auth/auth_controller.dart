import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../../core/auth/session_events.dart';
import '../../core/network/api_client.dart';
import '../../core/network/api_exceptions.dart';
import '../../core/realtime/ws_client.dart';
import '../../core/storage/secure_token_storage.dart';
import '../../models/staff_role.dart';
import '../../models/user.dart';

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());
final secureStorageProvider =
    Provider<SecureTokenStorage>((ref) => SecureTokenStorage());

/// Waiter-area realtime client. Only connected for WAITER sessions; the
/// Kitchen area owns its own client (see `kitchen/realtime`).
final wsClientProvider = Provider<WsClient>((ref) => WsClient());

class AuthState {
  /// True while a stored session is being re-verified with the backend.
  final bool isInitializing;
  final bool isLoading;
  final bool isAuthenticated;
  final User? user;
  final String? error;

  const AuthState({
    this.isInitializing = false,
    this.isLoading = false,
    this.isAuthenticated = false,
    this.user,
    this.error,
  });

  AuthState copyWith({
    bool? isInitializing,
    bool? isLoading,
    bool? isAuthenticated,
    User? user,
    String? error,
  }) {
    return AuthState(
      isInitializing: isInitializing ?? this.isInitializing,
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      user: user ?? this.user,
      error: error,
    );
  }

  /// Backend-verified role of the signed-in user, if it is one this app serves.
  StaffRole? get role =>
      isAuthenticated ? StaffRole.fromBackend(user?.role) : null;
}

class AuthController extends StateNotifier<AuthState> {
  final ApiClient _apiClient;
  final SecureTokenStorage _tokenStorage;
  final WsClient _wsClient;
  StreamSubscription<void>? _expiredSub;

  AuthController({
    required ApiClient apiClient,
    required SecureTokenStorage tokenStorage,
    required WsClient wsClient,
    bool restoreSession = true,
  })  : _apiClient = apiClient,
        _tokenStorage = tokenStorage,
        _wsClient = wsClient,
        super(AuthState(isInitializing: restoreSession)) {
    _expiredSub = SessionEvents.expired.listen((_) => _handleSessionExpired());
    if (restoreSession) {
      checkAuth();
    }
  }

  @override
  void dispose() {
    _expiredSub?.cancel();
    super.dispose();
  }

  /// Re-verifies a stored session with the backend (`GET /auth/me`).
  ///
  /// The locally stored role is never trusted on its own.
  Future<void> checkAuth() async {
    try {
      final token = await _tokenStorage.getAccessToken();
      if (token == null || token.isEmpty) {
        if (mounted) state = const AuthState();
        return;
      }

      final res = await _apiClient.get('/auth/me');
      final user = User.fromJson(res as Map<String, dynamic>);

      if (StaffRole.fromBackend(user.role) == null) {
        await _clearSession();
        if (mounted) {
          state = const AuthState(
            error: 'This account cannot use the staff app.',
          );
        }
        return;
      }

      // The access/refresh pair may have been rotated while calling /auth/me.
      final currentAccess = await _tokenStorage.getAccessToken() ?? token;
      await _tokenStorage.saveAuth(
        accessToken: currentAccess,
        userId: user.id,
        username: user.username,
        fullName: user.fullName,
        role: user.role,
        refreshToken: await _tokenStorage.getRefreshToken(),
      );

      if (!mounted) return;
      state = AuthState(isAuthenticated: true, user: user);
      if (user.role == StaffRole.waiter.backendValue) {
        _wsClient.connect(currentAccess);
      }
    } on AuthException {
      await _clearSession();
      if (mounted) state = const AuthState();
    } catch (_) {
      // Backend unreachable: fail closed (no dashboard) but keep the stored
      // session so a later successful sign-in simply replaces it.
      if (mounted) {
        state = const AuthState(
          error:
              'Could not verify your session. Check your connection and sign in again.',
        );
      }
    }
  }

  /// Signs in. [selectedRole] is only the user's stated intent: access is
  /// granted solely when the backend-verified role matches it.
  Future<bool> login(
    String username,
    String password,
    StaffRole selectedRole,
  ) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final res = await _apiClient.post(
        '/auth/login',
        body: {
          'username': username.trim(),
          'password': password,
          'client_type': selectedRole.clientType,
        },
      );

      final data = res as Map<String, dynamic>;
      final token = data['access_token']?.toString() ?? '';
      final user = User.fromJson(data['user'] as Map<String, dynamic>? ?? {});

      if (token.isEmpty || user.role.isEmpty) {
        state = state.copyWith(
          isLoading: false,
          isAuthenticated: false,
          error: 'Login failed: unexpected response from the server.',
        );
        return false;
      }

      // Role check happens BEFORE anything is persisted.
      if (user.role != selectedRole.backendValue) {
        await _revokeUnusedSession(token);
        state = state.copyWith(
          isLoading: false,
          isAuthenticated: false,
          error: _roleMismatchMessage(selectedRole),
        );
        return false;
      }

      await _tokenStorage.saveAuth(
        accessToken: token,
        userId: user.id,
        username: user.username,
        fullName: user.fullName,
        role: user.role,
        refreshToken: data['refresh_token']?.toString(),
      );

      state = AuthState(isAuthenticated: true, user: user);
      if (selectedRole == StaffRole.waiter) {
        _wsClient.connect(token);
      }
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: false,
        error: _friendlyError(e, selectedRole),
      );
      return false;
    }
  }

  /// Local logout is immediate and unconditional; server-side revocation is
  /// best effort so a dead network can never trap the user in a session.
  Future<void> logout() async {
    final accessToken = await _tokenStorage.getAccessToken();
    final refreshToken = await _tokenStorage.getRefreshToken();

    _wsClient.disconnect();
    await _clearSession();
    if (mounted) state = const AuthState();

    if (accessToken != null && accessToken.isNotEmpty) {
      try {
        await _apiClient.post(
          '/auth/logout',
          body: {
            if (refreshToken != null && refreshToken.isNotEmpty)
              'refresh_token': refreshToken,
          },
          headers: {'Authorization': 'Bearer $accessToken'},
        );
      } catch (_) {}
    }
  }

  Future<void> _handleSessionExpired() async {
    if (!mounted || !(state.isAuthenticated || state.isInitializing)) return;
    _wsClient.disconnect();
    await _clearSession();
    if (mounted) {
      state = const AuthState(
        error: 'Your session has expired. Please sign in again.',
      );
    }
  }

  Future<void> _clearSession() => _tokenStorage.clearAuth();

  /// A mismatched login still created a backend session; revoke it so no
  /// valid refresh token is left behind.
  Future<void> _revokeUnusedSession(String accessToken) async {
    try {
      await _apiClient.post(
        '/auth/logout',
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (_) {}
  }

  static String _roleMismatchMessage(StaffRole selected) =>
      'Access denied: this account does not have the ${selected.label} role. '
      'Select the correct role and try again.';

  static String _friendlyError(Object e, StaffRole selected) {
    if (e is ApiException) {
      if (e.code == 'ROLE_CLIENT_MISMATCH') {
        return _roleMismatchMessage(selected);
      }
      return e.message;
    }
    if (e is TimeoutException) {
      return 'The server took too long to respond. Check your connection and try again.';
    }
    if (e is http.ClientException) {
      return 'Network error: ${e.message}';
    }
    return 'Something went wrong. Please try again.';
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController(
    apiClient: ref.watch(apiClientProvider),
    tokenStorage: ref.watch(secureStorageProvider),
    wsClient: ref.watch(wsClientProvider),
  );
});
