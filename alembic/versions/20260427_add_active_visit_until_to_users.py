"""Add active_visit_until to users.

Revision ID: 20260427_add_active_visit_until
Revises: 20260413_add_phone_and_verified
Create Date: 2026-04-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "20260427_add_active_visit_until"
down_revision: str | None = "20260413_add_phone_and_verified"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("active_visit_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "active_visit_until")

