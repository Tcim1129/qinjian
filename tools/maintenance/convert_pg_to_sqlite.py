import re
import os

models_path = os.path.join('backend', 'app', 'models', '__init__.py')

with open(models_path, 'r', encoding='utf-8') as f:
    content = f.read()

# SQLite in SQLAlchemy 2.0 has good support for generic types
# but sqlalchemy.dialects.postgresql.UUID will fail on SQLite
# Replace postgresql UUID import with standard sqlalchemy Uuid or just mapping
content = content.replace(
    'from sqlalchemy.dialects.postgresql import UUID, JSONB',
    'from sqlalchemy import JSON as JSONB, Uuid as UUID'
)
content = content.replace(
    'from sqlalchemy.dialects.postgresql import UUID',
    'from sqlalchemy import Uuid as UUID'
)

# For JSONB fields, just map them to JSON for sqlite compatibility
content = content.replace('JSONB', 'JSON')

with open(models_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Models patched for SQLite")
