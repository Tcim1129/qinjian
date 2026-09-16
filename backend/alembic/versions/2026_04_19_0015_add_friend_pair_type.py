"""add friend pair type

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-19
"""

from alembic import op


revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE pairtype ADD VALUE IF NOT EXISTS 'friend'")


def downgrade():
    pass
