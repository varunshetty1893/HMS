import 'dart:async';
import 'package:http/http.dart' as http;

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

/// Turns any error into a short, readable message for the UI.
///
/// Backend errors show only their human message (never the
/// `ApiException(CODE): ...` debug form).
String describeError(Object e) {
  if (e is ApiException) {
    switch (e.code) {
      case 'PREPARING_MODIFICATION_BLOCKED':
        return 'This order is already being prepared by the kitchen, so it '
            'can no longer be changed or cancelled here. Please ask an admin.';
    }
    return e.message;
  }
  if (e is TimeoutException) {
    return 'The server took too long to respond. Check your connection and try again.';
  }
  if (e is http.ClientException) {
    return 'Network error. Check your connection and try again.';
  }
  return 'Something went wrong. Please try again.';
}
