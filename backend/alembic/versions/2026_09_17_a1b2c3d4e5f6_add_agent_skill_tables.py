"""add relationship_memories and skill_analysis_records

Revision ID: a1b2c3d4e5f6
Revises: f8cb965e7600
Create Date: 2026-09-17 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f8cb965e7600'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The first deployment of this revision could fall back to SQLAlchemy
    # ``create_all`` after a migration error.  Keep the revision retryable so
    # that the next startup can stamp it instead of attempting duplicate DDL.
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table('relationship_memories') and inspector.has_table('skill_analysis_records'):
        return

    op.create_table(
        'relationship_memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pair_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('memory_type', sa.String(20), nullable=False),
        sa.Column('subject', sa.String(100), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('source_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('importance', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('last_referenced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['pair_id'], ['pairs.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['source_session_id'], ['agent_chat_sessions.id']),
    )
    op.create_index('ix_relationship_memories_pair_id', 'relationship_memories', ['pair_id'])
    op.create_index('ix_relationship_memories_user_id', 'relationship_memories', ['user_id'])
    op.create_index('ix_relationship_memories_memory_type', 'relationship_memories', ['memory_type'])
    op.create_index('ix_relationship_memories_subject', 'relationship_memories', ['subject'])

    op.create_table(
        'skill_analysis_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pair_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_input', sa.Text(), nullable=False),
        sa.Column('primary_intent', sa.String(20), nullable=False),
        sa.Column('delivery_json', sa.JSON(), nullable=False),
        sa.Column('selected_proposal_id', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['pair_id'], ['pairs.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['session_id'], ['agent_chat_sessions.id']),
    )
    op.create_index('ix_skill_analysis_records_pair_id', 'skill_analysis_records', ['pair_id'])
    op.create_index('ix_skill_analysis_records_user_id', 'skill_analysis_records', ['user_id'])


def downgrade() -> None:
    op.drop_table('skill_analysis_records')
    op.drop_table('relationship_memories')
