class ApiException implements Exception {
  final String code;
  final String message;
  final int? statusCode;
  final Map<String, dynamic>? details;

  ApiException({
    required this.code,
    required this.message,
    this.statusCode,
    this.details,
  });

  @override
  String toString() => 'ApiException($code): $message (HTTP $statusCode)';
}

class VersionConflictException extends ApiException {
  VersionConflictException({
    super.code = 'ORDER_VERSION_CONFLICT',
    super.message = 'The order was updated by another staff member. Ticket refreshed.',
    super.statusCode = 409,
    super.details,
  });
}

class UnacknowledgedModificationsException extends ApiException {
  UnacknowledgedModificationsException({
    super.code = 'ORDER_MODIFICATIONS_UNACKNOWLEDGED',
    super.message = 'Please acknowledge order modifications before marking ready.',
    super.statusCode = 422,
    super.details,
  });
}

class AuthException extends ApiException {
  AuthException({
    super.code = 'UNAUTHORIZED',
    super.message = 'Invalid or expired session. Please log in again.',
    super.statusCode = 401,
  });
}
