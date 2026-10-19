# Fix 2: CI green (apply AFTER fix 1)

Copy these files over the repo (same paths), then `alembic upgrade head` (new migration 0013).

1. Ruff: all 25 errors fixed (`ruff check .` passes): unused imports, import order, long lines, `UP038`.
2. `alembic downgrade base` crashed at 0007 (NULL prices of seasonal items cannot become NOT NULL).
   The 0007 downgrade now sets those prices to 0 first. CI runs this step, so it was red.
3. CI: the pytest integration fixture needs an EMPTY database, but the migration step left it at head
   ("Refusing to run: test database already contains application tables"). `ci.yml` now ends that step
   with `alembic downgrade base`.
4. Schema drift test:
   - `order_items.adjustment_*_user_id` FKs now `ON DELETE RESTRICT` (migration 0013, as docs/04 requires).
   - `WaiterRequest.status` model now declares the `'PENDING'` server default the DB already had.
5. Old integration tests: table count 20 -> 21 (`waiter_requests`), and the unique-code test no longer
   clashes with the seeded menu code "CB".

Verified locally on PostgreSQL 16 in the CI order: ruff, upgrade -> downgrade base -> upgrade -> downgrade base,
then pytest: 397 passed, 0 skipped, 0 failed.
Not verified: GitHub Actions itself, and the Flutter `flutter analyze` job.
