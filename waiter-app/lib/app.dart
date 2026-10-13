import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'config/theme.dart';
import 'features/auth/auth_controller.dart';
import 'features/auth/login_screen.dart';
import 'features/floor_grid/floor_tables_screen.dart';
import 'kitchen/config/kds_theme.dart';
import 'kitchen/features/kds_board/kds_board_screen.dart';
import 'models/staff_role.dart';

final GlobalKey<NavigatorState> rootNavigatorKey = GlobalKey<NavigatorState>();

/// Single entry point for the combined staff app.
///
/// The dashboard is chosen from the *backend-verified* role held by
/// `AuthController`, never from the radio button on the login screen.
class StaffApp extends ConsumerWidget {
  const StaffApp({super.key});

  /// Role-based routing decision, kept pure so it can be unit tested.
  @visibleForTesting
  static Widget homeFor(AuthState auth) {
    if (auth.isInitializing) return const _SplashScreen();
    switch (auth.role) {
      case StaffRole.waiter:
        return const FloorTablesScreen();
      case StaffRole.kitchen:
        return const KdsBoardScreen();
      case null:
        return const LoginScreen();
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);

    // When the session ends (logout / expiry) drop any screens that were
    // pushed on top of the old dashboard so they cannot stay reachable.
    ref.listen<AuthState>(authControllerProvider, (previous, next) {
      if ((previous?.isAuthenticated ?? false) && !next.isAuthenticated) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          rootNavigatorKey.currentState?.popUntil((route) => route.isFirst);
        });
      }
    });

    return MaterialApp(
      navigatorKey: rootNavigatorKey,
      title: 'SpiceHub Staff',
      debugShowCheckedModeBanner: false,
      theme: auth.role == StaffRole.kitchen
          ? KdsTheme.lightTheme
          : AppTheme.lightTheme,
      home: homeFor(auth),
    );
  }
}

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}
