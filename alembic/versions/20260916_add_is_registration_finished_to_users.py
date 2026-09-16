"""Add is_registration_finished to users.

Revision ID: 20260916_add_is_registration_finished
Revises: 20260427_add_active_visit_until
Create Date: 2026-09-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "20260916_add_is_registration_finished"
down_revision: str | None = "20260427_add_active_visit_until"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_registration_finished",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_registration_finished")
