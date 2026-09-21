"""add agent_thoughts

Revision ID: f8cb965e7600
Revises: 0023
Create Date: 2026-07-31 02:46:14.835607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'f8cb965e7600'
down_revision: Union[str, None] = '0023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agent_thoughts',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('thought', sa.Text(), nullable=True),
        sa.Column('tool_calls_json', sa.Text(), nullable=True),
        sa.Column('tool_results_json', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['agent_chat_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_thoughts_session_id'), 'agent_thoughts', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_agent_thoughts_session_id'), table_name='agent_thoughts')
    op.drop_table('agent_thoughts')
