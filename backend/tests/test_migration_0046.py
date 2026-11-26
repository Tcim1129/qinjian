"""实际 SQLite 和 PostgreSQL 离线 SQL 验证新增追溯表迁移。"""
import importlib.util
import io
from pathlib import Path
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def migration():
    filename=Path(__file__).resolve().parents[1]/'alembic/versions/2026_11_18_0046_add_memory_removal_archives.py'
    spec=importlib.util.spec_from_file_location('migration_0046',filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_upgrade_downgrade_and_upgrade_again():
    engine=sa.create_engine('sqlite:///:memory:')
    with engine.begin() as connection:
        connection.execute(sa.text('CREATE TABLE users (id CHAR(36) PRIMARY KEY)'))
        connection.execute(sa.text('CREATE TABLE pairs (id CHAR(36) PRIMARY KEY)'))
        module=migration();module.op=Operations(MigrationContext.configure(connection))
        module.upgrade()
        assert 'memory_removal_archives' in sa.inspect(connection).get_table_names()
        assert any(index['name']=='uq_memory_removal_request_record' and index['unique'] for index in sa.inspect(connection).get_indexes('memory_removal_archives'))
        module.downgrade()
        assert 'memory_removal_archives' not in sa.inspect(connection).get_table_names()
        module.upgrade()
        assert 'snapshot_ciphertext' in {c['name'] for c in sa.inspect(connection).get_columns('memory_removal_archives')}
    engine.dispose()


def test_postgresql_migration_sql_compiles():
    output=io.StringIO()
    module=migration()
    module.op=Operations(MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':output}))
    module.upgrade()
    sql=output.getvalue()
    assert 'UUID' in sql and 'memory_removal_archives' in sql and 'UNIQUE INDEX' in sql
