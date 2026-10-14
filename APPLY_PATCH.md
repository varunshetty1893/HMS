# Order edit / force-cancel patch

1. Extract this zip INTO your project root (E:\git projects\HMS-main) and overwrite files.
2. Backend: `cd backend; alembic upgrade head`   (new migration 0003)
3. Restart uvicorn. Customer-web: `npm run dev`. Flutter apps: rebuild.
4. Tests: `pytest tests/api/test_order_edit_rules.py tests/api/test_orders_customer.py`
