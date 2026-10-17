import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/theme.dart';
import '../../models/staff_role.dart';
import 'auth_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;
  StaffRole? _selectedRole;
  String? _roleError;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    var username = _usernameController.text.trim();
    if (username.startsWith('@')) {
      username = username.substring(1).trim();
    }
    final password = _passwordController.text;

    if (_selectedRole == null) {
      setState(() => _roleError = 'Select your role to continue.');
      return;
    }
    if (username.isEmpty || password.isEmpty) return;

    final ok = await ref
        .read(authControllerProvider.notifier)
        .login(username, password, _selectedRole!);
    if (!ok && mounted) {
      // Never keep a rejected password in the field.
      _passwordController.clear();
    }
  }

  Widget _roleOption(StaffRole role, bool disabled) {
    return RadioListTile<StaffRole>(
      key: Key('role_${role.name}'),
      value: role,
      groupValue: _selectedRole,
      onChanged: disabled
          ? null
          : (value) => setState(() {
                _selectedRole = value;
                _roleError = null;
              }),
      title: Text(
        role.label,
        style: const TextStyle(
          color: WaiterTheme.textPrimary,
          fontWeight: FontWeight.w600,
        ),
      ),
      contentPadding: EdgeInsets.zero,
      dense: true,
      activeColor: WaiterTheme.primary,
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);

    return Scaffold(
      backgroundColor: WaiterTheme.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Card(
                color: WaiterTheme.surface,
                child: Padding(
                  padding: const EdgeInsets.all(28.0),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Center(
                        child: Container(
                          width: 68,
                          height: 68,
                          decoration: BoxDecoration(
                            color: WaiterTheme.primary.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                                color: WaiterTheme.primary, width: 2),
                          ),
                          child: const Icon(
                            Icons.restaurant_menu_rounded,
                            size: 38,
                            color: WaiterTheme.primary,
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      const Text(
                        'SpiceHub Staff',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: WaiterTheme.textPrimary,
                          fontSize: 22,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.5,
                        ),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Select your role and sign in',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: WaiterTheme.textMuted,
                          fontSize: 14,
                        ),
                      ),
                      const SizedBox(height: 28),
                      if (authState.error != null) ...[
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: WaiterTheme.errorRedBg,
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                                color: WaiterTheme.errorRed, width: 1),
                          ),
                          child: Text(
                            authState.error!,
                            style: const TextStyle(
                              color: WaiterTheme.errorRed,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],
                      const Text(
                        'I am signing in as',
                        style: TextStyle(
                          color: WaiterTheme.textMuted,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      _roleOption(StaffRole.waiter, authState.isLoading),
                      _roleOption(StaffRole.kitchen, authState.isLoading),
                      if (_roleError != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 4, bottom: 4),
                          child: Text(
                            _roleError!,
                            style: const TextStyle(
                              color: WaiterTheme.errorRed,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      const SizedBox(height: 12),
                      TextField(
                        key: const Key('username_field'),
                        controller: _usernameController,
                        style: const TextStyle(color: WaiterTheme.textPrimary),
                        decoration: const InputDecoration(
                          labelText: 'Username',
                          prefixIcon: Icon(Icons.badge_outlined,
                              color: WaiterTheme.textMuted),
                        ),
                        textInputAction: TextInputAction.next,
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        key: const Key('password_field'),
                        controller: _passwordController,
                        obscureText: _obscurePassword,
                        style: const TextStyle(color: WaiterTheme.textPrimary),
                        decoration: InputDecoration(
                          labelText: 'Password',
                          prefixIcon: const Icon(Icons.lock_outline,
                              color: WaiterTheme.textMuted),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscurePassword
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                              color: WaiterTheme.textMuted,
                            ),
                            onPressed: () => setState(
                                () => _obscurePassword = !_obscurePassword),
                          ),
                        ),
                        onSubmitted: (_) => _submit(),
                      ),
                      const SizedBox(height: 24),
                      ElevatedButton(
                        key: const Key('login_button'),
                        onPressed: authState.isLoading ? null : _submit,
                        child: authState.isLoading
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2.5,
                                  valueColor: AlwaysStoppedAnimation<Color>(
                                      Colors.white),
                                ),
                              )
                            : const Text('Sign In'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
