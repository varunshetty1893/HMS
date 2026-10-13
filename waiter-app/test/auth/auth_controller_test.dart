import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:waiter_app/core/auth/session_events.dart';
import 'package:waiter_app/core/network/api_client.dart';
import 'package:waiter_app/features/auth/auth_controller.dart';
import 'package:waiter_app/models/staff_role.dart';

import '../helpers/fakes.dart';

AuthController _controller(
  MockClient client,
  InMemoryTokenStorage storage,
  FakeWsClient ws,
) {
  final c = AuthController(
    apiClient: ApiClient(httpClient: client, tokenStorage: storage),
    tokenStorage: storage,
    wsClient: ws,
    restoreSession: false,
  );
  addTearDown(c.dispose);
  return c;
}

void main() {
  group('Login: backend-verified role must match the selected role', () {
    test('Waiter selected + WAITER account -> authenticated, waiter WS connected',
        () async {
      final requests = <http.Request>[];
      final client = MockClient((req) async {
        requests.add(req);
        return jsonResponse(loginBody('WAITER'), 200);
      });
      final storage = InMemoryTokenStorage();
      final ws = FakeWsClient();
      final c = _controller(client, storage, ws);

      final ok = await c.login(' staff1 ', 'password123', StaffRole.waiter);

      expect(ok, isTrue);
      expect(c.state.isAuthenticated, isTrue);
      expect(c.state.role, StaffRole.waiter);
      expect(c.state.error, isNull);
      expect(requests.single.url.path, '/api/v1/auth/login');
      final body = jsonDecode(requests.single.body) as Map<String, dynamic>;
      expect(body['username'], 'staff1');
      expect(body['client_type'], 'WAITER_APP');
      expect(await storage.getAccessToken(), 'access_1');
      expect(ws.connectedWith, ['access_1']);
    });

    test('Kitchen selected + KITCHEN account -> authenticated, no waiter WS',
        () async {
      final requests = <http.Request>[];
      final client = MockClient((req) async {
        requests.add(req);
        return jsonResponse(loginBody('KITCHEN'), 200);
      });
      final storage = InMemoryTokenStorage();
      final ws = FakeWsClient();
      final c = _controller(client, storage, ws);

      final ok = await c.login('staff1', 'password123', StaffRole.kitchen);

      expect(ok, isTrue);
      expect(c.state.role, StaffRole.kitchen);
      expect(
        (jsonDecode(requests.single.body) as Map)['client_type'],
        'KITCHEN_APP',
      );
      expect(ws.connectedWith, isEmpty);
    });

    for (final c in [
      (selected: StaffRole.waiter, actual: 'KITCHEN'),
      (selected: StaffRole.kitchen, actual: 'WAITER'),
      (selected: StaffRole.waiter, actual: 'ADMIN'),
      (selected: StaffRole.kitchen, actual: 'ADMIN'),
    ]) {
      test(
          'Role mismatch: selected ${c.selected.label}, account ${c.actual} '
          '-> denied, nothing stored, session revoked', () async {
        final logoutAuth = <String?>[];
        final client = MockClient((req) async {
          if (req.url.path.endsWith('/auth/logout')) {
            logoutAuth.add(req.headers['Authorization']);
            return jsonResponse({'status': 'LOGGED_OUT'}, 200);
          }
          return jsonResponse(loginBody(c.actual), 200);
        });
        final storage = InMemoryTokenStorage();
        final ws = FakeWsClient();
        final ctrl = _controller(client, storage, ws);

        final ok = await ctrl.login('staff1', 'password123', c.selected);

        expect(ok, isFalse);
        expect(ctrl.state.isAuthenticated, isFalse);
        expect(ctrl.state.user, isNull);
        expect(ctrl.state.error,
            contains('does not have the ${c.selected.label} role'));
        expect(storage.data, isEmpty);
        expect(ws.connectedWith, isEmpty);
        expect(logoutAuth, ['Bearer access_1']);
      });
    }

    test('Backend ROLE_CLIENT_MISMATCH (403) shows the same clear error',
        () async {
      final client = MockClient((req) async => jsonResponse({
            'error': {
              'code': 'ROLE_CLIENT_MISMATCH',
              'message': 'Waiters cannot log in to the Kitchen KDS.',
            },
          }, 403));
      final c = _controller(client, InMemoryTokenStorage(), FakeWsClient());

      final ok = await c.login('staff1', 'password123', StaffRole.kitchen);

      expect(ok, isFalse);
      expect(c.state.error, contains('does not have the Kitchen Staff role'));
    });

    test('Invalid credentials (401) -> error, nothing stored', () async {
      final client = MockClient((req) async => jsonResponse({
            'error': {
              'code': 'INVALID_CREDENTIALS',
              'message': 'Invalid username or password',
            },
          }, 401));
      final storage = InMemoryTokenStorage();
      final c = _controller(client, storage, FakeWsClient());

      final ok = await c.login('staff1', 'wrongpass1', StaffRole.waiter);

      expect(ok, isFalse);
      expect(c.state.isAuthenticated, isFalse);
      expect(c.state.error, contains('Invalid username or password'));
      expect(storage.data, isEmpty);
    });

    test('Network failure -> friendly error, not authenticated', () async {
      final client = MockClient((req) async {
        throw http.ClientException('Connection timed out', req.url);
      });
      final c = _controller(client, InMemoryTokenStorage(), FakeWsClient());

      final ok = await c.login('staff1', 'password123', StaffRole.waiter);

      expect(ok, isFalse);
      expect(c.state.isAuthenticated, isFalse);
      expect(c.state.error, contains('Connection timed out'));
    });
  });

  group('Logout', () {
    test('clears local session, disconnects WS and revokes server session',
        () async {
      final logoutRequests = <http.Request>[];
      final client = MockClient((req) async {
        if (req.url.path.endsWith('/auth/logout')) {
          logoutRequests.add(req);
          return jsonResponse({'status': 'LOGGED_OUT'}, 200);
        }
        return jsonResponse(loginBody('WAITER'), 200);
      });
      final storage = InMemoryTokenStorage();
      final ws = FakeWsClient();
      final c = _controller(client, storage, ws);
      await c.login('staff1', 'password123', StaffRole.waiter);

      await c.logout();

      expect(c.state.isAuthenticated, isFalse);
      expect(c.state.role, isNull);
      expect(storage.data, isEmpty);
      expect(ws.disconnectCount, greaterThanOrEqualTo(1));
      expect(logoutRequests, hasLength(1));
      expect(logoutRequests.single.headers['Authorization'], 'Bearer access_1');
      expect(
        (jsonDecode(logoutRequests.single.body) as Map)['refresh_token'],
        'refresh_1',
      );
    });

    test('still logs out locally when the server is unreachable', () async {
      final client = MockClient((req) async {
        if (req.url.path.endsWith('/auth/logout')) {
          throw http.ClientException('offline', req.url);
        }
        return jsonResponse(loginBody('KITCHEN'), 200);
      });
      final storage = InMemoryTokenStorage();
      final c = _controller(client, storage, FakeWsClient());
      await c.login('staff1', 'password123', StaffRole.kitchen);

      await c.logout();

      expect(c.state.isAuthenticated, isFalse);
      expect(storage.data, isEmpty);
    });
  });

  group('Session restore (/auth/me is the authority)', () {
    Future<InMemoryTokenStorage> storedSession(String storedRole) async {
      final s = InMemoryTokenStorage();
      await s.saveAuth(
        accessToken: 'stored_access',
        userId: 'u-1',
        username: 'staff1',
        fullName: 'Staff One',
        role: storedRole,
        refreshToken: 'stored_refresh',
      );
      return s;
    }

    test('no stored token -> unauthenticated, no network call', () async {
      var calls = 0;
      final client = MockClient((req) async {
        calls++;
        return jsonResponse({}, 200);
      });
      final c = _controller(client, InMemoryTokenStorage(), FakeWsClient());

      await c.checkAuth();

      expect(c.state.isAuthenticated, isFalse);
      expect(c.state.isInitializing, isFalse);
      expect(calls, 0);
    });

    test('valid WAITER session is restored and WS connected', () async {
      String? auth;
      final client = MockClient((req) async {
        expect(req.url.path, '/api/v1/auth/me');
        auth = req.headers['Authorization'];
        return jsonResponse(meBody('WAITER'), 200);
      });
      final storage = await storedSession('WAITER');
      final ws = FakeWsClient();
      final c = _controller(client, storage, ws);

      await c.checkAuth();

      expect(auth, 'Bearer stored_access');
      expect(c.state.role, StaffRole.waiter);
      expect(ws.connectedWith, ['stored_access']);
    });

    test('valid KITCHEN session is restored without waiter WS', () async {
      final client =
          MockClient((req) async => jsonResponse(meBody('KITCHEN'), 200));
      final ws = FakeWsClient();
      final c = _controller(client, await storedSession('KITCHEN'), ws);

      await c.checkAuth();

      expect(c.state.role, StaffRole.kitchen);
      expect(ws.connectedWith, isEmpty);
    });

    test('locally stored role is NOT trusted: backend role wins', () async {
      final client =
          MockClient((req) async => jsonResponse(meBody('WAITER'), 200));
      final storage = await storedSession('KITCHEN'); // tampered / stale
      final c = _controller(client, storage, FakeWsClient());

      await c.checkAuth();

      expect(c.state.role, StaffRole.waiter);
      expect(storage.data['role'], 'WAITER');
    });

    test('ADMIN session is rejected and cleared', () async {
      final client =
          MockClient((req) async => jsonResponse(meBody('ADMIN'), 200));
      final storage = await storedSession('ADMIN');
      final c = _controller(client, storage, FakeWsClient());

      await c.checkAuth();

      expect(c.state.isAuthenticated, isFalse);
      expect(c.state.error, contains('cannot use the staff app'));
      expect(storage.data, isEmpty);
    });

    test('expired/invalid token (401) clears the stored session', () async {
      final client = MockClient((req) async => jsonResponse({
            'error': {'code': 'TOKEN_EXPIRED', 'message': 'Token expired'},
          }, 401));
      final storage = await storedSession('WAITER');
      final c = _controller(client, storage, FakeWsClient());

      await c.checkAuth();

      expect(c.state.isAuthenticated, isFalse);
      expect(c.state.isInitializing, isFalse);
      expect(storage.data, isEmpty);
    });

    test('backend unreachable -> fail closed, stored tokens kept', () async {
      final client = MockClient((req) async {
        throw http.ClientException('offline', req.url);
      });
      final storage = await storedSession('WAITER');
      final c = _controller(client, storage, FakeWsClient());

      await c.checkAuth();

      expect(c.state.isAuthenticated, isFalse);
      expect(c.state.error, contains('Could not verify your session'));
      expect(await storage.getAccessToken(), 'stored_access');
    });
  });

  group('Session expiry', () {
    test('refresh rejection event logs the user out and clears storage',
        () async {
      final client =
          MockClient((req) async => jsonResponse(loginBody('WAITER'), 200));
      final storage = InMemoryTokenStorage();
      final ws = FakeWsClient();
      final c = _controller(client, storage, ws);
      await c.login('staff1', 'password123', StaffRole.waiter);
      expect(c.state.isAuthenticated, isTrue);

      SessionEvents.notifyExpired();
      await Future<void>.delayed(const Duration(milliseconds: 20));

      expect(c.state.isAuthenticated, isFalse);
      expect(c.state.error, contains('session has expired'));
      expect(storage.data, isEmpty);
      expect(ws.disconnectCount, greaterThanOrEqualTo(1));
    });
  });
}
