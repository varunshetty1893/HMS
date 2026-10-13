/// Roles that may sign in to the combined staff app.
///
/// The selected role is only a *preference* made on the login screen. The
/// backend-verified role returned by `/auth/login` and `/auth/me` is the
/// authority; see `AuthController`.
enum StaffRole {
  waiter,
  kitchen;

  /// Role string exactly as issued by the FastAPI backend.
  String get backendValue => this == StaffRole.waiter ? 'WAITER' : 'KITCHEN';

  /// `client_type` accepted by `POST /auth/login` (`StaffLoginRequest`).
  String get clientType => this == StaffRole.waiter ? 'WAITER_APP' : 'KITCHEN_APP';

  String get label => this == StaffRole.waiter ? 'Waiter' : 'Kitchen Staff';

  /// Returns null for any role the staff app does not serve (e.g. ADMIN).
  static StaffRole? fromBackend(String? role) {
    switch (role) {
      case 'WAITER':
        return StaffRole.waiter;
      case 'KITCHEN':
        return StaffRole.kitchen;
      default:
        return null;
    }
  }
}
