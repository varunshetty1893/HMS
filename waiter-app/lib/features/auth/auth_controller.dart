import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../core/realtime/ws_client.dart';
import '../../core/storage/secure_token_storage.dart';
import '../../models/user.dart';

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());
final secureStorageProvider =
    Provider<SecureTokenStorage>((ref) => SecureTokenStorage());
final wsClientProvider = Provider<WsClient>((ref) => WsClient());

class AuthState {
  final bool isLoading;
  final bool isAuthenticated;
  final User? user;
  final String? error;

  const AuthState({
    this.isLoading = false,
    this.isAuthenticated = false,
    this.user,
    this.error,
  });

  AuthState copyWith({
    bool? isLoading,
    bool? isAuthenticated,
    User? user,
    String? error,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      user: user ?? this.user,
      error: error,
    );
  }
}

class AuthController extends StateNotifier<AuthState> {
  final ApiClient _apiClient;
  final SecureTokenStorage _tokenStorage;
  final WsClient _wsClient;

  AuthController({
    required ApiClient apiClient,
    required SecureTokenStorage tokenStorage,
    required WsClient wsClient,
  })  : _apiClient = apiClient,
        _tokenStorage = tokenStorage,
        _wsClient = wsClient,
        super(const AuthState()) {
    checkAuth();
  }

  Future<void> checkAuth() async {
    final token = await _tokenStorage.getAccessToken();
    if (token != null && token.isNotEmpty) {
      final userId = await _tokenStorage.getUserId() ?? '';
      final username = await _tokenStorage.getUsername() ?? '';
      final fullName = await _tokenStorage.getFullName() ?? '';
      final role = await _tokenStorage.getRole() ?? 'WAITER';

      final user =
          User(id: userId, username: username, fullName: fullName, role: role);
      state = state.copyWith(isAuthenticated: true, user: user);
      _wsClient.connect(token);
    }
  }

  Future<bool> login(String username, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final res = await _apiClient.post(
        '/auth/login',
        body: {'username': username.trim(), 'password': password},
      );

      final token = res['access_token']?.toString() ?? '';
      final userData = res['user'] as Map<String, dynamic>? ?? {};
      final user = User.fromJson(userData);

      if (user.role != 'WAITER' && user.role != 'ADMIN') {
        state = state.copyWith(
          isLoading: false,
          error: 'Access denied: Waiter or Admin role required.',
        );
        return false;
      }

      await _tokenStorage.saveAuth(
        accessToken: token,
        userId: user.id,
        username: user.username,
        fullName: user.fullName,
        role: user.role,
        refreshToken: res['refresh_token']?.toString(),
      );

      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        user: user,
      );

      _wsClient.connect(token);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceFirst('ApiException', '').trim(),
      );
      return false;
    }
  }

  Future<void> logout() async {
    _wsClient.disconnect();
    await _tokenStorage.clearAuth();
    state = const AuthState();
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
