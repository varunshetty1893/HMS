"""initial_schema_20_tables

Revision ID: 0001
Revises: 
Create Date: 2026-10-09 05:17:37.607180+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Built-in contrib extension (no cost); powers the trigram dish-name index (`docs/04` Sec. 25).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table('idempotency_keys',
    sa.Column('idempotency_key', sa.String(length=128), nullable=False),
    sa.Column('actor_scope', sa.String(length=100), nullable=False),
    sa.Column('endpoint_path', sa.String(length=200), nullable=False),
    sa.Column('request_hash', sa.CHAR(length=64), nullable=False),
    sa.Column('response_status_code', sa.Integer(), nullable=False),
    sa.Column('response_body_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('expires_at > created_at', name=op.f('ck_idempotency_keys_expires_after_created')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_idempotency_keys')),
    sa.UniqueConstraint('idempotency_key', 'actor_scope', name='uq_idempotency_keys_key_actor_scope')
    )
    op.create_index('ix_idempotency_keys_expires_at', 'idempotency_keys', ['expires_at'], unique=False)
    op.create_table('menu_categories',
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('display_order >= 0', name=op.f('ck_menu_categories_display_order_non_negative')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_menu_categories'))
    )
    op.create_index('ix_menu_categories_is_active_display_order', 'menu_categories', ['is_active', 'display_order'], unique=False)
    op.create_index('uq_menu_categories_name_lower', 'menu_categories', [sa.literal_column('lower(name)')], unique=True)
    op.create_table('restaurant_tables',
    sa.Column('table_number', sa.Integer(), nullable=False),
    sa.Column('display_name', sa.String(length=50), nullable=False),
    sa.Column('seating_capacity', sa.Integer(), nullable=True),
    sa.Column('floor_or_zone', sa.String(length=50), nullable=True),
    sa.Column('operational_status', sa.String(length=20), server_default='ENABLED', nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('notes', sa.String(length=255), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("operational_status IN ('ENABLED','MAINTENANCE','DISABLED')", name=op.f('ck_restaurant_tables_status_valid')),
    sa.CheckConstraint('seating_capacity IS NULL OR seating_capacity > 0', name=op.f('ck_restaurant_tables_seating_capacity_positive')),
    sa.CheckConstraint('table_number > 0', name=op.f('ck_restaurant_tables_table_number_positive')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_restaurant_tables')),
    sa.UniqueConstraint('table_number', name=op.f('uq_restaurant_tables_table_number'))
    )
    op.create_index('ix_restaurant_tables_is_active_display_order', 'restaurant_tables', ['is_active', 'display_order'], unique=False)
    op.create_index('uq_restaurant_tables_display_name_lower', 'restaurant_tables', [sa.literal_column('lower(display_name)')], unique=True)
    op.create_table('users',
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='ACTIVE', nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('failed_login_attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('password_changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('token_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_by_user_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role IN ('ADMIN','WAITER','KITCHEN')", name=op.f('ck_users_role_valid')),
    sa.CheckConstraint("status IN ('ACTIVE','DISABLED','LOCKED')", name=op.f('ck_users_status_valid')),
    sa.CheckConstraint('failed_login_attempts >= 0', name=op.f('ck_users_failed_login_attempts_non_negative')),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_users_created_by_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index('ix_users_role_is_active', 'users', ['role', 'is_active'], unique=False)
    op.create_index('uq_users_username_lower', 'users', [sa.literal_column('lower(username)')], unique=True)
    op.create_table('menu_items',
    sa.Column('category_id', sa.UUID(), nullable=False),
    sa.Column('item_code', sa.String(length=16), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('dietary_type', sa.String(length=15), nullable=True),
    sa.Column('spice_level', sa.String(length=15), nullable=True),
    sa.Column('image_url', sa.String(length=500), nullable=True),
    sa.Column('tax_rate_override', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('is_available', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("btrim(item_code) <> ''", name=op.f('ck_menu_items_item_code_not_blank')),
    sa.CheckConstraint("dietary_type IS NULL OR dietary_type IN ('VEG','NON_VEG','EGG')", name=op.f('ck_menu_items_dietary_type_valid')),
    sa.CheckConstraint("spice_level IS NULL OR spice_level IN ('MILD','MEDIUM','HOT')", name=op.f('ck_menu_items_spice_level_valid')),
    sa.ForeignKeyConstraint(['category_id'], ['menu_categories.id'], name=op.f('fk_menu_items_category_id_menu_categories'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_menu_items'))
    )
    op.create_index('ix_menu_items_category_active_available_order', 'menu_items', ['category_id', 'is_active', 'is_available', 'display_order'], unique=False)
    op.create_index('ix_menu_items_name_trgm', 'menu_items', [sa.literal_column('lower(name) gin_trgm_ops')], unique=False, postgresql_using='gin')
    op.create_index('uq_menu_items_item_code_upper', 'menu_items', [sa.literal_column('upper(item_code)')], unique=True)
    op.create_table('restaurant_settings',
    sa.Column('id', sa.Integer(), server_default=sa.text('1'), autoincrement=False, nullable=False),
    sa.Column('restaurant_name', sa.String(length=120), nullable=False),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('gstin', sa.String(length=15), nullable=True),
    sa.Column('logo_url', sa.String(length=500), nullable=True),
    sa.Column('currency_code', sa.String(length=3), server_default='INR', nullable=False),
    sa.Column('currency_symbol', sa.String(length=5), server_default='₹', nullable=False),
    sa.Column('prices_include_tax', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('cgst_percentage', sa.Numeric(precision=5, scale=2), server_default=sa.text('2.50'), nullable=False),
    sa.Column('sgst_percentage', sa.Numeric(precision=5, scale=2), server_default=sa.text('2.50'), nullable=False),
    sa.Column('service_charge_percentage', sa.Numeric(precision=5, scale=2), server_default=sa.text('0.00'), nullable=False),
    sa.Column('allowed_payment_methods_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('default_session_outstanding_limit', sa.Numeric(precision=10, scale=2), server_default=sa.text('5000.00'), nullable=False),
    sa.Column('is_ordering_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('opening_time', sa.Time(), nullable=True),
    sa.Column('closing_time', sa.Time(), nullable=True),
    sa.Column('allow_multi_device_per_table', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('allow_customer_cancel_placed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('allow_waiter_cancel_preparing_item', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('allow_kitchen_mark_served', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('kitchen_can_toggle_availability', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('limit_includes_estimated_tax', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('apply_outstanding_limit_to_waiter_orders', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('waiter_max_discount_percentage', sa.Numeric(precision=5, scale=2), server_default=sa.text('0.00'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by_user_id', sa.UUID(), nullable=True),
    sa.CheckConstraint('cgst_percentage >= 0', name=op.f('ck_restaurant_settings_cgst_non_negative')),
    sa.CheckConstraint('default_session_outstanding_limit > 0', name=op.f('ck_restaurant_settings_default_outstanding_limit_positive')),
    sa.CheckConstraint('id = 1', name=op.f('ck_restaurant_settings_singleton_row')),
    sa.CheckConstraint('service_charge_percentage >= 0', name=op.f('ck_restaurant_settings_service_charge_non_negative')),
    sa.CheckConstraint('sgst_percentage >= 0', name=op.f('ck_restaurant_settings_sgst_non_negative')),
    sa.CheckConstraint('waiter_max_discount_percentage >= 0 AND waiter_max_discount_percentage <= 100', name=op.f('ck_restaurant_settings_waiter_max_discount_range')),
    sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], name=op.f('fk_restaurant_settings_updated_by_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_restaurant_settings'))
    )
    op.create_table('staff_refresh_tokens',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.CHAR(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('is_revoked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_reason', sa.String(length=100), nullable=True),
    sa.Column('device_label', sa.String(length=100), nullable=True),
    sa.Column('replaced_by_token_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('expires_at > created_at', name=op.f('ck_staff_refresh_tokens_expires_after_created')),
    sa.ForeignKeyConstraint(['replaced_by_token_id'], ['staff_refresh_tokens.id'], name='fk_staff_refresh_tokens_replaced_by_token_id', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_staff_refresh_tokens_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_staff_refresh_tokens')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_staff_refresh_tokens_token_hash'))
    )
    op.create_index('ix_staff_refresh_tokens_expires_at', 'staff_refresh_tokens', ['expires_at'], unique=False)
    op.create_index('ix_staff_refresh_tokens_user_id_is_revoked', 'staff_refresh_tokens', ['user_id', 'is_revoked'], unique=False)
    op.create_table('table_qr_tokens',
    sa.Column('table_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.CHAR(length=64), nullable=False),
    sa.Column('token_prefix', sa.String(length=10), nullable=False),
    sa.Column('printable_token_ciphertext', sa.Text(), nullable=False),
    sa.Column('token_version', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_by_user_id', sa.UUID(), nullable=False),
    sa.Column('activated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('revoked_by_user_id', sa.UUID(), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revocation_reason', sa.String(length=255), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('ACTIVE','SUPERSEDED','REVOKED','DISABLED')", name=op.f('ck_table_qr_tokens_status_valid')),
    sa.CheckConstraint('token_version >= 1', name=op.f('ck_table_qr_tokens_token_version_positive')),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_table_qr_tokens_created_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['revoked_by_user_id'], ['users.id'], name=op.f('fk_table_qr_tokens_revoked_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['table_id'], ['restaurant_tables.id'], name=op.f('fk_table_qr_tokens_table_id_restaurant_tables'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_table_qr_tokens')),
    sa.UniqueConstraint('table_id', 'token_version', name='uq_table_qr_tokens_table_id_version'),
    sa.UniqueConstraint('token_hash', name=op.f('uq_table_qr_tokens_token_hash'))
    )
    op.create_index('uq_qr_tokens_one_active_per_table', 'table_qr_tokens', ['table_id'], unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))
    op.create_table('table_sessions',
    sa.Column('session_code', sa.String(length=32), nullable=False),
    sa.Column('table_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('opened_by_source', sa.String(length=20), nullable=False),
    sa.Column('opened_by_customer_session_id', sa.UUID(), nullable=True),
    sa.Column('opened_by_user_id', sa.UUID(), nullable=True),
    sa.Column('current_outstanding_amount', sa.Numeric(precision=10, scale=2), server_default=sa.text('0.00'), nullable=False),
    sa.Column('custom_outstanding_limit', sa.Numeric(precision=10, scale=2), server_default=sa.text('5000.00'), nullable=False),
    sa.Column('limit_override_by_user_id', sa.UUID(), nullable=True),
    sa.Column('limit_override_reason', sa.String(length=255), nullable=True),
    sa.Column('is_locked_for_abuse', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closed_by_user_id', sa.UUID(), nullable=True),
    sa.Column('closed_reason', sa.String(length=255), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("opened_by_source IN ('CUSTOMER_QR','WAITER')", name=op.f('ck_table_sessions_opened_by_source_valid')),
    sa.CheckConstraint("status IN ('ACTIVE','CLOSED_PAID','CLOSED_CANCELLED','CLOSED_ADMIN_OVERRIDE')", name=op.f('ck_table_sessions_status_valid')),
    sa.CheckConstraint('current_outstanding_amount >= 0', name=op.f('ck_table_sessions_outstanding_non_negative')),
    sa.CheckConstraint('custom_outstanding_limit > 0', name=op.f('ck_table_sessions_outstanding_limit_positive')),
    sa.ForeignKeyConstraint(['closed_by_user_id'], ['users.id'], name=op.f('fk_table_sessions_closed_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['limit_override_by_user_id'], ['users.id'], name=op.f('fk_table_sessions_limit_override_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['opened_by_user_id'], ['users.id'], name=op.f('fk_table_sessions_opened_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['table_id'], ['restaurant_tables.id'], name=op.f('fk_table_sessions_table_id_restaurant_tables'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_table_sessions')),
    sa.UniqueConstraint('session_code', name=op.f('uq_table_sessions_session_code'))
    )
    op.create_index('ix_table_sessions_status_started_at', 'table_sessions', ['status', sa.literal_column('started_at DESC')], unique=False)
    op.create_index('uq_table_sessions_one_open_per_table', 'table_sessions', ['table_id'], unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))
    op.create_table('bills',
    sa.Column('bill_number', sa.String(length=32), nullable=False),
    sa.Column('table_session_id', sa.UUID(), nullable=False),
    sa.Column('table_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=25), nullable=False),
    sa.Column('subtotal_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), server_default=sa.text('0.00'), nullable=False),
    sa.Column('discount_reason', sa.String(length=255), nullable=True),
    sa.Column('discount_approved_by_user_id', sa.UUID(), nullable=True),
    sa.Column('taxable_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('cgst_rate_snapshot', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('cgst_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('sgst_rate_snapshot', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('sgst_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('service_charge_amount', sa.Numeric(precision=10, scale=2), server_default=sa.text('0.00'), nullable=False),
    sa.Column('rounding_adjustment', sa.Numeric(precision=5, scale=2), server_default=sa.text('0.00'), nullable=False),
    sa.Column('grand_total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('generated_by_user_id', sa.UUID(), nullable=False),
    sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('voided_by_user_id', sa.UUID(), nullable=True),
    sa.Column('void_reason', sa.String(length=255), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('ISSUED','PAID','VOIDED_FOR_REVISION')", name=op.f('ck_bills_status_valid')),
    sa.CheckConstraint('cgst_amount >= 0', name=op.f('ck_bills_cgst_non_negative')),
    sa.CheckConstraint('discount_amount = 0 OR discount_reason IS NOT NULL', name=op.f('ck_bills_discount_reason_required')),
    sa.CheckConstraint('discount_amount >= 0 AND discount_amount <= subtotal_amount', name=op.f('ck_bills_discount_in_range')),
    sa.CheckConstraint('grand_total >= 0', name=op.f('ck_bills_grand_total_non_negative')),
    sa.CheckConstraint('service_charge_amount >= 0', name=op.f('ck_bills_service_charge_non_negative')),
    sa.CheckConstraint('sgst_amount >= 0', name=op.f('ck_bills_sgst_non_negative')),
    sa.CheckConstraint('subtotal_amount >= 0', name=op.f('ck_bills_subtotal_non_negative')),
    sa.CheckConstraint('taxable_amount = subtotal_amount - discount_amount', name=op.f('ck_bills_taxable_matches')),
    sa.ForeignKeyConstraint(['discount_approved_by_user_id'], ['users.id'], name=op.f('fk_bills_discount_approved_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['generated_by_user_id'], ['users.id'], name=op.f('fk_bills_generated_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['table_id'], ['restaurant_tables.id'], name=op.f('fk_bills_table_id_restaurant_tables'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['table_session_id'], ['table_sessions.id'], name=op.f('fk_bills_table_session_id_table_sessions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['voided_by_user_id'], ['users.id'], name=op.f('fk_bills_voided_by_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bills')),
    sa.UniqueConstraint('bill_number', name=op.f('uq_bills_bill_number'))
    )
    op.create_index('ix_bills_status_generated_at', 'bills', ['status', sa.literal_column('generated_at DESC')], unique=False)
    op.create_index('uq_bills_one_active_per_session', 'bills', ['table_session_id'], unique=True, postgresql_where=sa.text("status IN ('ISSUED','PAID')"))
    op.create_table('customer_sessions',
    sa.Column('table_id', sa.UUID(), nullable=False),
    sa.Column('qr_token_id', sa.UUID(), nullable=False),
    sa.Column('table_session_id', sa.UUID(), nullable=True),
    sa.Column('session_token_hash', sa.CHAR(length=64), nullable=False),
    sa.Column('status', sa.String(length=25), nullable=False),
    sa.Column('client_fingerprint_hash', sa.CHAR(length=64), nullable=True),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_reason', sa.String(length=100), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('ACTIVE','LOCKED_SUSPICIOUS','EXPIRED','CLOSED_BY_PAYMENT','REVOKED')", name=op.f('ck_customer_sessions_status_valid')),
    sa.ForeignKeyConstraint(['qr_token_id'], ['table_qr_tokens.id'], name=op.f('fk_customer_sessions_qr_token_id_table_qr_tokens'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['table_id'], ['restaurant_tables.id'], name=op.f('fk_customer_sessions_table_id_restaurant_tables'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['table_session_id'], ['table_sessions.id'], name=op.f('fk_customer_sessions_table_session_id_table_sessions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_customer_sessions')),
    sa.UniqueConstraint('session_token_hash', name=op.f('uq_customer_sessions_session_token_hash'))
    )
    op.create_index('ix_customer_sessions_table_id_status', 'customer_sessions', ['table_id', 'status'], unique=False)
    op.create_index('ix_customer_sessions_table_session_id_status', 'customer_sessions', ['table_session_id', 'status'], unique=False)
    # Circular dependency: table_sessions <-> customer_sessions. The back-reference FK is added
    # after both tables exist (SQLAlchemy `use_alter=True`).
    op.create_foreign_key(
        'fk_table_sessions_opened_by_customer_session_id',
        'table_sessions',
        'customer_sessions',
        ['opened_by_customer_session_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_table('menu_price_variants',
    sa.Column('menu_item_id', sa.UUID(), nullable=False),
    sa.Column('variant_code', sa.String(length=24), nullable=True),
    sa.Column('variant_name', sa.String(length=80), nullable=False),
    sa.Column('quantity_value', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('is_default', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_available', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("unit IN ('PORTION','PIECE','ML','L','GRAM','KG','PLATE','BOWL','GLASS','BOTTLE')", name=op.f('ck_menu_price_variants_unit_valid')),
    sa.CheckConstraint('price >= 0', name=op.f('ck_menu_price_variants_price_non_negative')),
    sa.CheckConstraint('quantity_value > 0', name=op.f('ck_menu_price_variants_quantity_value_positive')),
    sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id'], name=op.f('fk_menu_price_variants_menu_item_id_menu_items'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_menu_price_variants'))
    )
    op.create_index('ix_menu_price_variants_item_active_available_order', 'menu_price_variants', ['menu_item_id', 'is_active', 'is_available', 'display_order'], unique=False)
    op.create_index('uq_menu_price_variants_item_variant_name_lower', 'menu_price_variants', ['menu_item_id', sa.literal_column('lower(variant_name)')], unique=True)
    op.create_index('uq_menu_price_variants_variant_code_upper', 'menu_price_variants', [sa.literal_column('upper(variant_code)')], unique=True, postgresql_where=sa.text('variant_code IS NOT NULL'))
    op.create_table('audit_logs',
    sa.Column('actor_user_id', sa.UUID(), nullable=True),
    sa.Column('actor_customer_session_id', sa.UUID(), nullable=True),
    sa.Column('actor_role', sa.String(length=20), nullable=False),
    sa.Column('action_type', sa.String(length=60), nullable=False),
    sa.Column('entity_type', sa.String(length=60), nullable=False),
    sa.Column('entity_id', sa.String(length=64), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.Column('old_value_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('new_value_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('ip_hash', sa.CHAR(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.CheckConstraint("actor_role IN ('CUSTOMER','WAITER','KITCHEN','ADMIN','SYSTEM')", name=op.f('ck_audit_logs_actor_role_valid')),
    sa.ForeignKeyConstraint(['actor_customer_session_id'], ['customer_sessions.id'], name=op.f('fk_audit_logs_actor_customer_session_id_customer_sessions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name=op.f('fk_audit_logs_actor_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index('ix_audit_logs_action_type_created_at', 'audit_logs', ['action_type', sa.literal_column('created_at DESC')], unique=False)
    op.create_index('ix_audit_logs_actor_user_id_created_at', 'audit_logs', ['actor_user_id', sa.literal_column('created_at DESC')], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', [sa.literal_column('created_at DESC')], unique=False)
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id', sa.literal_column('created_at DESC')], unique=False)
    op.create_table('orders',
    sa.Column('order_number', sa.String(length=32), nullable=False),
    sa.Column('table_session_id', sa.UUID(), nullable=False),
    sa.Column('table_id', sa.UUID(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('customer_session_id', sa.UUID(), nullable=True),
    sa.Column('created_by_user_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('order_subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('special_instructions', sa.String(length=500), nullable=True),
    sa.Column('is_first_qr_order_of_session', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('has_unacknowledged_mods', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('placed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('accepted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('preparing_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('preparing_by_user_id', sa.UUID(), nullable=True),
    sa.Column('ready_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ready_by_user_id', sa.UUID(), nullable=True),
    sa.Column('served_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('served_by_user_id', sa.UUID(), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rejected_by_user_id', sa.UUID(), nullable=True),
    sa.Column('rejection_reason', sa.String(length=255), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cancelled_by_user_id', sa.UUID(), nullable=True),
    sa.Column('cancelled_by_role', sa.String(length=20), nullable=True),
    sa.Column('cancellation_reason', sa.String(length=255), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("source IN ('CUSTOMER_QR','WAITER')", name=op.f('ck_orders_source_valid')),
    sa.CheckConstraint("status <> 'CANCELLED' OR cancellation_reason IS NOT NULL", name=op.f('ck_orders_cancellation_reason_required')),
    sa.CheckConstraint("status <> 'REJECTED' OR rejection_reason IS NOT NULL", name=op.f('ck_orders_rejection_reason_required')),
    sa.CheckConstraint("status IN ('PLACED','ACCEPTED','PREPARING','READY','SERVED','COMPLETED','REJECTED','CANCELLED')", name=op.f('ck_orders_status_valid')),
    sa.CheckConstraint('order_subtotal >= 0', name=op.f('ck_orders_subtotal_non_negative')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_orders_version_positive')),
    sa.ForeignKeyConstraint(['accepted_by_user_id'], ['users.id'], name=op.f('fk_orders_accepted_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['cancelled_by_user_id'], ['users.id'], name=op.f('fk_orders_cancelled_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_orders_created_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['customer_session_id'], ['customer_sessions.id'], name=op.f('fk_orders_customer_session_id_customer_sessions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['preparing_by_user_id'], ['users.id'], name=op.f('fk_orders_preparing_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['ready_by_user_id'], ['users.id'], name=op.f('fk_orders_ready_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['rejected_by_user_id'], ['users.id'], name=op.f('fk_orders_rejected_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['served_by_user_id'], ['users.id'], name=op.f('fk_orders_served_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['table_id'], ['restaurant_tables.id'], name=op.f('fk_orders_table_id_restaurant_tables'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['table_session_id'], ['table_sessions.id'], name=op.f('fk_orders_table_session_id_table_sessions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_orders')),
    sa.UniqueConstraint('order_number', name=op.f('uq_orders_order_number'))
    )
    op.create_index('ix_orders_created_by_user_id_placed_at', 'orders', ['created_by_user_id', sa.literal_column('placed_at DESC')], unique=False)
    op.create_index('ix_orders_kitchen_queue', 'orders', ['status', 'placed_at'], unique=False, postgresql_where=sa.text("status IN ('PLACED','ACCEPTED','PREPARING','READY')"))
    op.create_index('ix_orders_table_session_id_placed_at', 'orders', ['table_session_id', 'placed_at'], unique=False)
    op.create_index('ix_orders_table_session_id_status', 'orders', ['table_session_id', 'status'], unique=False)
    op.create_table('payments',
    sa.Column('bill_id', sa.UUID(), nullable=False),
    sa.Column('table_session_id', sa.UUID(), nullable=False),
    sa.Column('payment_method', sa.String(length=20), nullable=False),
    sa.Column('amount_paid', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('reference_number', sa.String(length=100), nullable=True),
    sa.Column('notes', sa.String(length=255), nullable=True),
    sa.Column('recorded_by_user_id', sa.UUID(), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failed_or_voided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failure_or_void_reason', sa.String(length=255), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("payment_method IN ('CASH','UPI','CARD','OTHER')", name=op.f('ck_payments_method_valid')),
    sa.CheckConstraint("status IN ('PENDING','COMPLETED','FAILED','VOIDED')", name=op.f('ck_payments_status_valid')),
    sa.CheckConstraint('amount_paid > 0', name=op.f('ck_payments_amount_paid_positive')),
    sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], name=op.f('fk_payments_bill_id_bills'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['recorded_by_user_id'], ['users.id'], name=op.f('fk_payments_recorded_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['table_session_id'], ['table_sessions.id'], name=op.f('fk_payments_table_session_id_table_sessions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_payments'))
    )
    op.create_index('ix_payments_bill_id_status', 'payments', ['bill_id', 'status'], unique=False)
    op.create_index('ix_payments_completed_at_payment_method', 'payments', [sa.literal_column('completed_at DESC'), 'payment_method'], unique=False, postgresql_where=sa.text("status = 'COMPLETED'"))
    op.create_index('uq_payments_one_completed_per_bill', 'payments', ['bill_id'], unique=True, postgresql_where=sa.text("status = 'COMPLETED'"))
    op.create_table('notifications',
    sa.Column('event_type', sa.String(length=40), nullable=False),
    sa.Column('target_channel', sa.String(length=20), nullable=False),
    sa.Column('severity', sa.String(length=10), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=False),
    sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('requires_acknowledgment', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_acknowledged', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('table_id', sa.UUID(), nullable=True),
    sa.Column('table_session_id', sa.UUID(), nullable=True),
    sa.Column('order_id', sa.UUID(), nullable=True),
    sa.Column('target_user_id', sa.UUID(), nullable=True),
    sa.Column('acknowledged_by_user_id', sa.UUID(), nullable=True),
    sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("severity IN ('INFO','WARNING','CRITICAL')", name=op.f('ck_notifications_severity_valid')),
    sa.CheckConstraint("target_channel IN ('KITCHEN_ALL','WAITERS_ALL','ADMIN_ALL','USER_SPECIFIC','TABLE_SESSION')", name=op.f('ck_notifications_channel_valid')),
    sa.ForeignKeyConstraint(['acknowledged_by_user_id'], ['users.id'], name=op.f('fk_notifications_acknowledged_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_notifications_order_id_orders'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['table_id'], ['restaurant_tables.id'], name=op.f('fk_notifications_table_id_restaurant_tables'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['table_session_id'], ['table_sessions.id'], name=op.f('fk_notifications_table_session_id_table_sessions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], name=op.f('fk_notifications_target_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    op.create_index('ix_notifications_channel_ack_created_at', 'notifications', ['target_channel', 'is_acknowledged', sa.literal_column('created_at DESC')], unique=False)
    op.create_index('ix_notifications_table_session_id_created_at', 'notifications', ['table_session_id', sa.literal_column('created_at DESC')], unique=False)
    op.create_table('order_items',
    sa.Column('order_id', sa.UUID(), nullable=False),
    sa.Column('menu_item_id', sa.UUID(), nullable=False),
    sa.Column('menu_price_variant_id', sa.UUID(), nullable=False),
    sa.Column('item_code_snapshot', sa.String(length=16), nullable=False),
    sa.Column('item_name_snapshot', sa.String(length=150), nullable=False),
    sa.Column('variant_code_snapshot', sa.String(length=24), nullable=True),
    sa.Column('variant_name_snapshot', sa.String(length=80), nullable=False),
    sa.Column('quantity_value_snapshot', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('unit_snapshot', sa.String(length=20), nullable=False),
    sa.Column('unit_price_snapshot', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('tax_rate_snapshot', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('original_quantity', sa.Integer(), nullable=False),
    sa.Column('active_quantity', sa.Integer(), nullable=False),
    sa.Column('cancelled_quantity', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('line_subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('item_status', sa.String(length=20), server_default='ACTIVE', nullable=False),
    sa.Column('item_notes', sa.String(length=255), nullable=True),
    sa.Column('cancellation_reason', sa.String(length=255), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("item_status IN ('ACTIVE','MODIFIED','CANCELLED')", name=op.f('ck_order_items_item_status_valid')),
    sa.CheckConstraint('active_quantity >= 0', name=op.f('ck_order_items_active_quantity_non_negative')),
    sa.CheckConstraint('cancelled_quantity >= 0', name=op.f('ck_order_items_cancelled_quantity_non_negative')),
    sa.CheckConstraint('line_subtotal = active_quantity * unit_price_snapshot', name=op.f('ck_order_items_line_subtotal_matches')),
    sa.CheckConstraint('original_quantity >= 1', name=op.f('ck_order_items_original_quantity_positive')),
    sa.CheckConstraint('unit_price_snapshot >= 0', name=op.f('ck_order_items_unit_price_snapshot_non_negative')),
    sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id'], name=op.f('fk_order_items_menu_item_id_menu_items'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['menu_price_variant_id'], ['menu_price_variants.id'], name=op.f('fk_order_items_menu_price_variant_id_menu_price_variants'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_order_items_order_id_orders'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_order_items'))
    )
    op.create_index('ix_order_items_menu_item_id', 'order_items', ['menu_item_id'], unique=False)
    op.create_index('ix_order_items_order_id_item_status', 'order_items', ['order_id', 'item_status'], unique=False)
    op.create_table('order_status_history',
    sa.Column('order_id', sa.UUID(), nullable=False),
    sa.Column('previous_status', sa.String(length=20), nullable=True),
    sa.Column('new_status', sa.String(length=20), nullable=False),
    sa.Column('changed_by_role', sa.String(length=20), nullable=False),
    sa.Column('changed_by_user_id', sa.UUID(), nullable=True),
    sa.Column('changed_by_customer_session_id', sa.UUID(), nullable=True),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.CheckConstraint("changed_by_role IN ('CUSTOMER','WAITER','KITCHEN','ADMIN','SYSTEM')", name=op.f('ck_order_status_history_changed_by_role_valid')),
    sa.CheckConstraint("new_status IN ('PLACED','ACCEPTED','PREPARING','READY','SERVED','COMPLETED','REJECTED','CANCELLED')", name=op.f('ck_order_status_history_new_status_valid')),
    sa.CheckConstraint("previous_status IS NULL OR previous_status IN ('PLACED','ACCEPTED','PREPARING','READY','SERVED','COMPLETED','REJECTED','CANCELLED')", name=op.f('ck_order_status_history_previous_status_valid')),
    sa.ForeignKeyConstraint(['changed_by_customer_session_id'], ['customer_sessions.id'], name='fk_order_status_history_changed_by_customer_session_id', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], name=op.f('fk_order_status_history_changed_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_order_status_history_order_id_orders'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_order_status_history'))
    )
    op.create_index('ix_order_status_history_order_id_changed_at', 'order_status_history', ['order_id', 'changed_at'], unique=False)
    op.create_table('bill_items',
    sa.Column('bill_id', sa.UUID(), nullable=False),
    sa.Column('order_id', sa.UUID(), nullable=False),
    sa.Column('order_item_id', sa.UUID(), nullable=False),
    sa.Column('order_number_snapshot', sa.String(length=32), nullable=False),
    sa.Column('item_code_snapshot', sa.String(length=16), nullable=False),
    sa.Column('item_name_snapshot', sa.String(length=150), nullable=False),
    sa.Column('variant_code_snapshot', sa.String(length=24), nullable=True),
    sa.Column('variant_name_snapshot', sa.String(length=80), nullable=False),
    sa.Column('unit_snapshot', sa.String(length=20), nullable=False),
    sa.Column('quantity_billed', sa.Integer(), nullable=False),
    sa.Column('unit_price_snapshot', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('line_total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('line_total = quantity_billed * unit_price_snapshot', name=op.f('ck_bill_items_line_total_matches')),
    sa.CheckConstraint('quantity_billed >= 1', name=op.f('ck_bill_items_quantity_billed_positive')),
    sa.CheckConstraint('unit_price_snapshot >= 0', name=op.f('ck_bill_items_unit_price_snapshot_non_negative')),
    sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], name=op.f('fk_bill_items_bill_id_bills'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_bill_items_order_id_orders'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id'], name=op.f('fk_bill_items_order_item_id_order_items'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bill_items'))
    )
    op.create_index('ix_bill_items_bill_id', 'bill_items', ['bill_id'], unique=False)
    op.create_table('order_modification_events',
    sa.Column('order_id', sa.UUID(), nullable=False),
    sa.Column('order_item_id', sa.UUID(), nullable=False),
    sa.Column('modification_type', sa.String(length=25), nullable=False),
    sa.Column('order_status_at_modification', sa.String(length=20), nullable=False),
    sa.Column('previous_quantity', sa.Integer(), nullable=False),
    sa.Column('new_quantity', sa.Integer(), nullable=False),
    sa.Column('previous_notes', sa.Text(), nullable=True),
    sa.Column('new_notes', sa.Text(), nullable=True),
    sa.Column('unit_price_snapshot', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('price_delta', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=False),
    sa.Column('modified_by_user_id', sa.UUID(), nullable=False),
    sa.Column('modified_by_role', sa.String(length=20), nullable=False),
    sa.Column('kitchen_ack_required', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('acknowledged_by_kitchen_user_id', sa.UUID(), nullable=True),
    sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("btrim(reason) <> ''", name=op.f('ck_order_modification_events_reason_not_blank')),
    sa.CheckConstraint("modification_type IN ('ITEM_ADDED','QUANTITY_INCREASED','QUANTITY_DECREASED','ITEM_CANCELLED','NOTES_UPDATED')", name=op.f('ck_order_modification_events_type_valid')),
    sa.CheckConstraint('new_quantity >= 0', name=op.f('ck_order_modification_events_new_quantity_non_negative')),
    sa.CheckConstraint('previous_quantity >= 0', name=op.f('ck_order_modification_events_previous_quantity_non_negative')),
    sa.ForeignKeyConstraint(['acknowledged_by_kitchen_user_id'], ['users.id'], name='fk_order_modification_events_ack_kitchen_user_id', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['modified_by_user_id'], ['users.id'], name=op.f('fk_order_modification_events_modified_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_order_modification_events_order_id_orders'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id'], name=op.f('fk_order_modification_events_order_item_id_order_items'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_order_modification_events'))
    )
    op.create_index('ix_order_modification_events_order_id_created_at', 'order_modification_events', ['order_id', 'created_at'], unique=False)
    op.create_index('ix_order_modification_events_pending_kitchen_ack', 'order_modification_events', ['kitchen_ack_required', 'acknowledged_at'], unique=False, postgresql_where=sa.text('kitchen_ack_required = true AND acknowledged_at IS NULL'))
    # Immutable audit trail (`docs/04` Sec. 22; `docs/13` Phase 2): block UPDATE and DELETE.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_log_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only; % is not permitted', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_prevent_audit_log_mutation
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_log_mutation ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_mutation()")
    # Break the circular FK before dropping either table.
    op.drop_constraint('fk_table_sessions_opened_by_customer_session_id', 'table_sessions', type_='foreignkey')
    # pg_trgm is intentionally NOT dropped: it may be shared with other objects in the database.
    op.drop_index('ix_order_modification_events_pending_kitchen_ack', table_name='order_modification_events', postgresql_where=sa.text('kitchen_ack_required = true AND acknowledged_at IS NULL'))
    op.drop_index('ix_order_modification_events_order_id_created_at', table_name='order_modification_events')
    op.drop_table('order_modification_events')
    op.drop_index('ix_bill_items_bill_id', table_name='bill_items')
    op.drop_table('bill_items')
    op.drop_index('ix_order_status_history_order_id_changed_at', table_name='order_status_history')
    op.drop_table('order_status_history')
    op.drop_index('ix_order_items_order_id_item_status', table_name='order_items')
    op.drop_index('ix_order_items_menu_item_id', table_name='order_items')
    op.drop_table('order_items')
    op.drop_index('ix_notifications_table_session_id_created_at', table_name='notifications')
    op.drop_index('ix_notifications_channel_ack_created_at', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('uq_payments_one_completed_per_bill', table_name='payments', postgresql_where=sa.text("status = 'COMPLETED'"))
    op.drop_index('ix_payments_completed_at_payment_method', table_name='payments', postgresql_where=sa.text("status = 'COMPLETED'"))
    op.drop_index('ix_payments_bill_id_status', table_name='payments')
    op.drop_table('payments')
    op.drop_index('ix_orders_table_session_id_status', table_name='orders')
    op.drop_index('ix_orders_table_session_id_placed_at', table_name='orders')
    op.drop_index('ix_orders_kitchen_queue', table_name='orders', postgresql_where=sa.text("status IN ('PLACED','ACCEPTED','PREPARING','READY')"))
    op.drop_index('ix_orders_created_by_user_id_placed_at', table_name='orders')
    op.drop_table('orders')
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_actor_user_id_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action_type_created_at', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index('uq_menu_price_variants_variant_code_upper', table_name='menu_price_variants', postgresql_where=sa.text('variant_code IS NOT NULL'))
    op.drop_index('uq_menu_price_variants_item_variant_name_lower', table_name='menu_price_variants')
    op.drop_index('ix_menu_price_variants_item_active_available_order', table_name='menu_price_variants')
    op.drop_table('menu_price_variants')
    op.drop_index('ix_customer_sessions_table_session_id_status', table_name='customer_sessions')
    op.drop_index('ix_customer_sessions_table_id_status', table_name='customer_sessions')
    op.drop_table('customer_sessions')
    op.drop_index('uq_bills_one_active_per_session', table_name='bills', postgresql_where=sa.text("status IN ('ISSUED','PAID')"))
    op.drop_index('ix_bills_status_generated_at', table_name='bills')
    op.drop_table('bills')
    op.drop_index('uq_table_sessions_one_open_per_table', table_name='table_sessions', postgresql_where=sa.text("status = 'ACTIVE'"))
    op.drop_index('ix_table_sessions_status_started_at', table_name='table_sessions')
    op.drop_table('table_sessions')
    op.drop_index('uq_qr_tokens_one_active_per_table', table_name='table_qr_tokens', postgresql_where=sa.text("status = 'ACTIVE'"))
    op.drop_table('table_qr_tokens')
    op.drop_index('ix_staff_refresh_tokens_user_id_is_revoked', table_name='staff_refresh_tokens')
    op.drop_index('ix_staff_refresh_tokens_expires_at', table_name='staff_refresh_tokens')
    op.drop_table('staff_refresh_tokens')
    op.drop_table('restaurant_settings')
    op.drop_index('uq_menu_items_item_code_upper', table_name='menu_items')
    op.drop_index('ix_menu_items_name_trgm', table_name='menu_items', postgresql_using='gin')
    op.drop_index('ix_menu_items_category_active_available_order', table_name='menu_items')
    op.drop_table('menu_items')
    op.drop_index('uq_users_username_lower', table_name='users')
    op.drop_index('ix_users_role_is_active', table_name='users')
    op.drop_table('users')
    op.drop_index('uq_restaurant_tables_display_name_lower', table_name='restaurant_tables')
    op.drop_index('ix_restaurant_tables_is_active_display_order', table_name='restaurant_tables')
    op.drop_table('restaurant_tables')
    op.drop_index('uq_menu_categories_name_lower', table_name='menu_categories')
    op.drop_index('ix_menu_categories_is_active_display_order', table_name='menu_categories')
    op.drop_table('menu_categories')
    op.drop_index('ix_idempotency_keys_expires_at', table_name='idempotency_keys')
    op.drop_table('idempotency_keys')
