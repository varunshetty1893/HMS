import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:waiter_app/app.dart';
import 'package:waiter_app/core/network/api_client.dart';
import 'package:waiter_app/features/auth/auth_controller.dart';
import 'package:waiter_app/features/auth/login_screen.dart';
import 'package:waiter_app/features/floor_grid/floor_tables_screen.dart';
import 'package:waiter_app/kitchen/features/kds_board/kds_board_screen.dart';
import 'package:waiter_app/models/staff_role.dart';
import 'package:waiter_app/models/user.dart';

import '../helpers/fakes.dart';

AuthState _signedIn(String role) => AuthState(
      isAuthenticated: true,
      user: User(id: 'u-1', username: 'staff1', fullName: 'Staff One', role: role),
    );

Widget _app(MockClient client, InMemoryTokenStorage storage) {
  return ProviderScope(
    overrides: [
      apiClientProvider.overrideWithValue(
        ApiClient(httpClient: client, tokenStorage: storage),
      ),
      secureStorageProvider.overrideWithValue(storage),
      wsClientProvider.overrideWithValue(FakeWsClient()),
    ],
    child: const StaffApp(),
  );
}

Future<void> _openLogin(WidgetTester tester, Widget app) async {
  await tester.binding.setSurfaceSize(const Size(800, 1400));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  await tester.pumpWidget(app);
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 50));
}

void main() {
  group('Dashboard access is decided by the backend-verified role', () {
    test('unauthenticated -> login screen', () {
      expect(StaffApp.homeFor(const AuthState()), isA<LoginScreen>());
    });

    test('initializing -> not the login screen (no flash)', () {
      expect(
        StaffApp.homeFor(const AuthState(isInitializing: true)),
        isNot(isA<LoginScreen>()),
      );
    });

    test('WAITER -> waiter dashboard', () {
      expect(StaffApp.homeFor(_signedIn('WAITER')), isA<FloorTablesScreen>());
    });

    test('KITCHEN -> kitchen dashboard', () {
      expect(StaffApp.homeFor(_signedIn('KITCHEN')), isA<KdsBoardScreen>());
    });

    test('ADMIN or unknown role -> never reaches a dashboard', () {
      expect(StaffApp.homeFor(_signedIn('ADMIN')), isA<LoginScreen>());
      expect(StaffApp.homeFor(_signedIn('???')), isA<LoginScreen>());
    });

    test('user data without isAuthenticated -> login screen', () {
      final state = AuthState(
        user: const User(
            id: 'u', username: 'w', fullName: 'W', role: 'WAITER'),
      );
      expect(state.role, isNull);
      expect(StaffApp.homeFor(state), isA<LoginScreen>());
    });

    test('StaffRole maps only WAITER and KITCHEN', () {
      expect(StaffRole.fromBackend('WAITER'), StaffRole.waiter);
      expect(StaffRole.fromBackend('KITCHEN'), StaffRole.kitchen);
      expect(StaffRole.fromBackend('ADMIN'), isNull);
      expect(StaffRole.fromBackend(null), isNull);
    });
  });

  group('Login screen', () {
    testWidgets('offers Waiter / Kitchen Staff radios; nothing preselected or prefilled',
        (tester) async {
      await _openLogin(
          tester, _app(MockClient((r) async => jsonResponse({}, 200)), InMemoryTokenStorage()));

      expect(find.byKey(const Key('role_waiter')), findsOneWidget);
      expect(find.byKey(const Key('role_kitchen')), findsOneWidget);
      expect(find.text('Waiter'), findsOneWidget);
      expect(find.text('Kitchen Staff'), findsOneWidget);
      expect(
        tester.widget<TextField>(find.byKey(const Key('username_field'))).controller!.text,
        isEmpty,
      );
      final tile = tester.widget<RadioListTile<StaffRole>>(
          find.byKey(const Key('role_waiter')));
      expect(tile.groupValue, isNull);
    });

    testWidgets('submitting without a role is blocked and sends nothing',
        (tester) async {
      var requests = 0;
      final client = MockClient((r) async {
        requests++;
        return jsonResponse({}, 200);
      });
      await _openLogin(tester, _app(client, InMemoryTokenStorage()));

      await tester.enterText(find.byKey(const Key('username_field')), 'staff1');
      await tester.enterText(find.byKey(const Key('password_field')), 'password123');
      await tester.tap(find.byKey(const Key('login_button')));
      await tester.pump();

      expect(find.text('Select your role to continue.'), findsOneWidget);
      expect(requests, 0);
    });

    testWidgets('role mismatch shows a clear error, stays on login, clears password',
        (tester) async {
      final client = MockClient((req) async {
        if (req.url.path.endsWith('/auth/logout')) {
          return jsonResponse({'status': 'LOGGED_OUT'}, 200);
        }
        return jsonResponse(loginBody('WAITER'), 200);
      });
      final storage = InMemoryTokenStorage();
      await _openLogin(tester, _app(client, storage));

      await tester.tap(find.byKey(const Key('role_kitchen')));
      await tester.pump();
      await tester.enterText(find.byKey(const Key('username_field')), 'waiter1');
      await tester.enterText(find.byKey(const Key('password_field')), 'password123');
      await tester.tap(find.byKey(const Key('login_button')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.textContaining('does not have the Kitchen Staff role'), findsOneWidget);
      expect(find.byKey(const Key('login_button')), findsOneWidget);
      expect(
        tester.widget<TextField>(find.byKey(const Key('password_field'))).controller!.text,
        isEmpty,
      );
      expect(storage.data, isEmpty);
    });
  });
}
