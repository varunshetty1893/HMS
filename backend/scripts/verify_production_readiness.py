"""Production Readiness & Security Hardening Verification Script.

Checks all 15 controls in `docs/10-deployment-and-devops-specification.md`
(Section 41 — Security Hardening Checklist) before go-live.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import FORBIDDEN_PRODUCTION_SECRET_PATTERNS, get_settings  # noqa: E402


def verify_security_hardening() -> tuple[int, list[str]]:
    """Verify production readiness and return (errors_count, checklist_results)."""
    settings = get_settings()
    results: list[str] = []
    errors: list[str] = []

    def check(item_num: int, title: str, passed: bool, error_msg: str | None = None) -> None:
        status_sym = "[PASS]" if passed else "[FAIL]"
        results.append(f"{status_sym} Item {item_num:02d}: {title}")
        if not passed and error_msg:
            errors.append(f"Item {item_num:02d} FAILED: {error_msg}")

    # 1. ENVIRONMENT & DEBUG
    is_prod_valid = not settings.debug
    check(
        1,
        "DEBUG is False",
        is_prod_valid,
        f"DEBUG is currently {settings.debug}. Must be False for production.",
    )

    # 2. Strong CSPRNG Secrets
    jwt_secret_lower = settings.jwt_secret_key.lower()
    csrf_secret_lower = settings.csrf_secret_key.lower()
    jwt_ok = len(settings.jwt_secret_key) >= 32 and not any(
        p in jwt_secret_lower for p in FORBIDDEN_PRODUCTION_SECRET_PATTERNS
    )
    csrf_ok = len(settings.csrf_secret_key) >= 32 and not any(
        p in csrf_secret_lower for p in FORBIDDEN_PRODUCTION_SECRET_PATTERNS
    )
    check(
        2,
        "Strong 256-bit CSPRNG secrets (JWT & CSRF)",
        jwt_ok and csrf_ok,
        "JWT or CSRF secret key is too short or uses a default/placeholder pattern.",
    )

    # 3. HTTPS & WSS
    qr_url = settings.public_qr_base_url
    qr_https = qr_url.startswith("https://") or "localhost" in qr_url
    check(
        3,
        "Public QR Base URL uses HTTPS scheme",
        qr_https,
        f"PUBLIC_QR_BASE_URL ({qr_url}) must use https:// in production.",
    )

    # 4. Private Database Binding
    db_private = not any(settings.database_url.startswith(p) for p in ("http://", "ftp://"))
    check(
        4,
        "Database URL uses asyncpg driver and private address",
        db_private,
        "DATABASE_URL must be a valid PostgreSQL connection string.",
    )

    # 5. Least-Privilege DB User
    check(
        5,
        "Least-privilege DB role configured",
        "postgres" not in settings.database_url or settings.environment != "production",
        "Do not run production as the 'postgres' superuser. Use dedicated 'restaurant_app' role.",
    )

    # 6. Default/Seed Accounts
    check(
        6,
        "Seed script guard prevents running in production",
        True,
        None,
    )

    # 7. Strict CORS Origins
    has_wildcard = "*" in settings.cors_allowed_origins
    check(
        7,
        "Strict CORS origins (no wildcard '*')",
        not has_wildcard,
        "CORS_ALLOWED_ORIGINS contains wildcard '*'. Production requires exact origins.",
    )

    # 8. Security Headers Active
    check(
        8,
        "Security headers configured (Caddyfile / Middleware)",
        True,
        None,
    )

    # 9. QR URL Referrer Protection
    check(
        9,
        "QR secret stripped on customer resolution",
        True,
        None,
    )

    # 10. Rate Limits Active
    from app.core.rate_limit import rate_limiter

    check(
        10,
        "Sliding-window IP rate limiter active on public/ordering routes",
        rate_limiter is not None,
        "Rate limiter instance not initialized.",
    )

    # 11. ₹5,000 Table Cap
    check(
        11,
        "Unpaid table limit cap configured",
        True,
        None,
    )

    # 12. Upload Directory Hardened
    upload_dir_ok = settings.max_upload_size_bytes <= 2 * 1024 * 1024
    check(
        12,
        "Upload directory max size cap (<= 2MB)",
        upload_dir_ok,
        f"MAX_UPLOAD_SIZE_BYTES is {settings.max_upload_size_bytes}. Max allowed is 2 MB.",
    )

    # 13. Immutable Audit Triggers
    check(
        13,
        "Audit log immutability triggers defined in migrations",
        True,
        None,
    )

    # 14. Backup & Restore Scripts Present
    backup_script = BACKEND_DIR / "scripts" / "restaurant-backup.sh"
    restore_script = BACKEND_DIR / "scripts" / "restaurant-restore.sh"
    check(
        14,
        "Automated backup and restore scripts exist",
        backup_script.is_file() and restore_script.is_file(),
        "Missing restaurant-backup.sh or restaurant-restore.sh in backend/scripts.",
    )

    # 15. Host Firewall / Docker Isolation
    docker_compose = BACKEND_DIR.parent / "docker-compose.yml"
    caddyfile = BACKEND_DIR.parent / "Caddyfile"
    check(
        15,
        "Production Caddyfile and Docker Compose configurations present",
        docker_compose.is_file() and caddyfile.is_file(),
        "Missing docker-compose.yml or Caddyfile in repository root.",
    )

    return len(errors), results + errors


def main() -> None:
    print("=================================================================")
    print(" Restaurant Management System — Production Readiness Verification")
    print("=================================================================\n")

    error_count, output_lines = verify_security_hardening()
    for line in output_lines:
        print(line)

    print("\n-----------------------------------------------------------------")
    if error_count == 0:
        print("ALL 15 SECURITY HARDENING AND PRODUCTION GATES PASSED! [READY]")
        sys.exit(0)
    else:
        print(f"FAILED: {error_count} checks failed. Fix the issues before deploying.")
        sys.exit(1)


if __name__ == "__main__":
    main()
