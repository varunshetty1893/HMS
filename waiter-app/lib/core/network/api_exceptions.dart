class ApiException implements Exception {
  final String code;
  final String message;
  final Map<String, dynamic>? details;

  const ApiException({
    required this.code,
    required this.message,
    this.details,
  });

  @override
  String toString() => 'ApiException($code): $message';
}

class AuthException extends ApiException {
  const AuthException({required super.code, required super.message});
}

class VersionConflictException extends ApiException {
  const VersionConflictException({
    required super.code,
    required super.message,
    super.details,
  });
}

/// Alias used by screens.
class ConflictException extends ApiException {
  const ConflictException({
    required super.code,
    required super.message,
    super.details,
  });
}

class TableLimitExceededException extends ApiException {
  const TableLimitExceededException({
    required super.code,
    required super.message,
    super.details,
  });
}
