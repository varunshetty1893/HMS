import 'dart:async';

/// App-wide signal raised when the backend rejects the stored session
/// (refresh token invalid/expired/revoked). `AuthController` listens and
/// performs a safe local logout.
class SessionEvents {
  SessionEvents._();

  static final StreamController<void> _expired =
      StreamController<void>.broadcast();

  static Stream<void> get expired => _expired.stream;

  static void notifyExpired() {
    if (!_expired.isClosed) _expired.add(null);
  }
}
