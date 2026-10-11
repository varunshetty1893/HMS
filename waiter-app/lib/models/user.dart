class User {
  final String id;
  final String username;
  final String fullName;
  final String role;

  const User({
    required this.id,
    required this.username,
    required this.fullName,
    required this.role,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      role: json['role']?.toString() ?? '',
    );
  }

  bool get isWaiter => role == 'WAITER';
  bool get isAdmin => role == 'ADMIN';
}
