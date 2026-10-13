"""The Alembic chain must apply cleanly to an empty database and roll back fully."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _alembic_config(url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def test_migrations_upgrade_and_downgrade(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'migrations.db'}"
    config = _alembic_config(url)
    engine = create_engine(url)

    command.upgrade(config, "head")
    tables = set(inspect(engine).get_table_names())
    assert {"doctors", "appointments", "alembic_version"} <= tables
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM doctors")).scalar() == 6

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()
