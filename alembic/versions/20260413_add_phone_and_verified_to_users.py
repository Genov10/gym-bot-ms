"""Add phone_number and is_verified to users.

Revision ID: 20260413_add_phone_and_verified
Revises: 
Create Date: 2026-04-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "20260413_add_phone_and_verified"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.String(length=32), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "is_verified")
    op.drop_column("users", "phone_number")

