import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../core/storage/secure_token_storage.dart';
import '../../models/user_model.dart';

class AuthState {
  final bool isLoading;
  final bool isAuthenticated;
  final UserModel? user;
  final String? errorMessage;

  const AuthState({
    this.isLoading = false,
    this.isAuthenticated = false,
    this.user,
    this.errorMessage,
  });

  AuthState copyWith({
    bool? isLoading,
    bool? isAuthenticated,
    UserModel? user,
    String? errorMessage,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      user: user ?? this.user,
      errorMessage: errorMessage,
    );
  }
}

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());
final tokenStorageProvider = Provider<SecureTokenStorage>((ref) => SecureTokenStorage());

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController(
    apiClient: ref.read(apiClientProvider),
    tokenStorage: ref.read(tokenStorageProvider),
  );
});

class AuthController extends StateNotifier<AuthState> {
  final ApiClient _apiClient;
  final SecureTokenStorage _tokenStorage;

  AuthController({
    required ApiClient apiClient,
    required SecureTokenStorage tokenStorage,
  })  : _apiClient = apiClient,
        _tokenStorage = tokenStorage,
        super(const AuthState()) {
    checkInitialAuth();
  }

  Future<void> checkInitialAuth() async {
    final token = await _tokenStorage.getAccessToken();
    final role = await _tokenStorage.getUserRole();
    final username = await _tokenStorage.getUsername();

    if (token != null && token.isNotEmpty && (role == 'KITCHEN' || role == 'ADMIN')) {
      state = state.copyWith(
        isAuthenticated: true,
        user: UserModel(
          id: '',
          username: username ?? 'staff',
          fullName: username ?? 'Kitchen Staff',
          role: role ?? 'KITCHEN',
        ),
      );
    }
  }

  Future<bool> login(String username, String password) async {
    state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      final res = await _apiClient.loginStaff(username: username, password: password);
      final userJson = res['user'] as Map<String, dynamic>;
      final user = UserModel.fromJson(userJson);

      if (user.role != 'KITCHEN' && user.role != 'ADMIN') {
        await _tokenStorage.clear();
        state = state.copyWith(
          isLoading: false,
          isAuthenticated: false,
          errorMessage: 'Access restricted: Only Kitchen and Admin staff may log into KDS.',
        );
        return false;
      }

      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        user: user,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString().replaceFirst('ApiException: ', ''),
      );
      return false;
    }
  }

  Future<void> logout() async {
    await _tokenStorage.clear();
    state = const AuthState(isAuthenticated: false);
  }
}
