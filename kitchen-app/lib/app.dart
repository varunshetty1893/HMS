import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'config/theme.dart';
import 'features/auth/auth_controller.dart';
import 'features/auth/login_screen.dart';
import 'features/kds_board/kds_board_screen.dart';

class KdsApp extends ConsumerWidget {
  const KdsApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authControllerProvider);

    return MaterialApp(
      title: 'SpiceHub Chef',
      debugShowCheckedModeBanner: false,
      theme: KdsTheme.lightTheme,
      home: authState.isAuthenticated ? const KdsBoardScreen() : const LoginScreen(),
    );
  }
}
