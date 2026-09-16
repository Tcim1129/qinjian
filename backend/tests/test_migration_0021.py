from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def load_migration_0021():
    root = Path(__file__).resolve().parents[1]
    migration_path = (
        root
        / "alembic"
        / "versions"
        / "2026_04_23_0021_add_task_planner_settings_and_priority.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0021", migration_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeInspector:
    def get_table_names(self):
        return ["pairs", "relationship_tasks"]

    def get_columns(self, table_name):
        if table_name == "pairs":
            return [{"name": "id"}]
        if table_name == "relationship_tasks":
            return [{"name": "id"}]
        return []


class FakeOp:
    def __init__(self):
        self.conn = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
        self.executed_sql: list[str] = []

    def get_bind(self):
        return self.conn

    def add_column(self, *_args, **_kwargs):
        return None

    def execute(self, sql: str):
        self.executed_sql.append(sql)


def test_migration_0021_casts_enum_to_text_before_empty_string_compare(monkeypatch):
    migration = load_migration_0021()
    fake_op = FakeOp()

    monkeypatch.setattr(migration, "op", fake_op)
    monkeypatch.setattr(migration.sa, "inspect", lambda _conn: FakeInspector())

    migration.upgrade()

    update_sql = next(
        sql for sql in fake_op.executed_sql if sql.startswith("UPDATE relationship_tasks")
    )
    assert "importance_level::text = ''" in update_sql
    assert " OR importance_level = ''" not in update_sql
