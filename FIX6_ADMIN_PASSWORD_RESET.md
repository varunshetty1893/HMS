# FIX6 — Admin password reset

1. **Change Password page** (admin-web sidebar -> "Change Password")
   - POST /api/v1/auth/change-password (current + new, min 8). Wrong current -> 422, same password -> 422.
   - Server revokes all refresh tokens, bumps token_version, drops WebSockets; page auto-logs out.
2. **Forgot password?** on admin login
   - POST /api/v1/auth/admin-recovery-reset (username + recovery key + new password).
   - Works ONLY if server env `ADMIN_RECOVERY_KEY` (16+ chars) is set (Render: Environment tab). Unset = disabled.
   - ADMIN role only, unlocks locked account, 5 tries / 15 min per IP, constant-time compare,
     one generic error for every failure, audited (ADMIN_RECOVERY_RESET / _FAILED).
   - Tip: set the key, reset, then remove/rotate it.

Tests: backend/tests/api/test_admin_password_reset.py (9 cases) — auth/table/billing suites pass. admin-web tsc clean.
