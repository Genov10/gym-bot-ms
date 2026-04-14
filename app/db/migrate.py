from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import settings


def _alembic_config() -> Config:
    # /app/app/db/migrate.py -> /app
    project_root = Path(__file__).resolve().parents[2]
    ini_path = project_root / "alembic.ini"

    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(project_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def upgrade_head() -> None:
    # Ensure cwd differences don't break relative paths
    os.chdir(Path(__file__).resolve().parents[2])
    command.upgrade(_alembic_config(), "head")

