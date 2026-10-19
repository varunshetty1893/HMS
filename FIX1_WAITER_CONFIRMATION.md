# Fix 1: waiter confirmation for the first QR order (threat T-01)

Apply: copy these files over the repo (same paths), then run `alembic upgrade head` (migration 0012).
Rollback: `alembic downgrade 0011` (held requests are cancelled first).

## Behaviour
- Table has no ACTIVE session + setting ON (default) -> QR order is held as PENDING_CONFIRMATION.
  Table stays AVAILABLE, kitchen sees nothing, billing ignores it.
- Waiter taps "Guests are seated" -> order PLACED, session ACTIVE, kitchen notified.
- Waiter taps Reject -> order REJECTED. No answer in `qr_confirmation_timeout_seconds` (default 180)
  -> order CANCELLED (SYSTEM). Guest can also withdraw. Guest sees "ask a waiter for help".
- One held request per table; restaurant-wide cap `max_pending_qr_confirmations` (default 15).
- If a waiter opens the table while a request is held, Confirm merges it into that session.

## API
GET  /api/v1/waiter/order-confirmations
POST /api/v1/waiter/orders/{id}/confirm
POST /api/v1/waiter/orders/{id}/reject
Settings: require_waiter_confirmation_for_first_qr_order, qr_confirmation_timeout_seconds,
max_pending_qr_confirmations (Admin -> Settings).

## Verified
Backend unit/API tests, 11 new real-PostgreSQL flow tests, migration up/down/up, customer-web and
admin-web `tsc` + build. NOT compiled: waiter-app (Flutter) - no SDK was available.
Three older integration tests already fail on the original upload (table count 21 vs 20,
5 FK drift items, seeded menu code 'cb'); unchanged by this fix.

## Known gap (not fixed here)
After the first order is confirmed, anyone with a photo of that table's QR can still add orders to the
open session until the bill is paid (limited by the Rs 5,000 cap and rate limits).
