"""Add is_registration_finished to users.

Revision ID: 20260916_add_reg_finished
Revises: 20260427_add_active_visit_until
Create Date: 2026-09-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# version_num in alembic_version is VARCHAR(32) — keep revision id <= 32 chars
revision: str = "20260916_add_reg_finished"
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
