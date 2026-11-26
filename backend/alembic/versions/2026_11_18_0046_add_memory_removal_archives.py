"""记忆停用后的限期加密追溯副本。"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision='0046'
down_revision='0045'
branch_labels=None
depends_on=None


def upgrade():
    uid=sa.CHAR(36).with_variant(postgresql.UUID(as_uuid=True),'postgresql')
    op.create_table('memory_removal_archives',
        sa.Column('id',uid,primary_key=True),
        sa.Column('user_id',uid,sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('pair_id',uid,sa.ForeignKey('pairs.id',ondelete='CASCADE'),nullable=False),
        sa.Column('memory_id',uid,nullable=False),
        sa.Column('request_message_id',uid,nullable=False),
        sa.Column('confirmation_message_id',uid,nullable=False),
        sa.Column('snapshot_ciphertext',sa.Text(),nullable=True),
        sa.Column('content_digest',sa.String(64),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False),
        sa.Column('retain_until',sa.DateTime(),nullable=False),
        sa.Column('audit_until',sa.DateTime(),nullable=False))
    for field in ['user_id','pair_id','retain_until','audit_until']:
        op.create_index('ix_memory_removal_archives_'+field,'memory_removal_archives',[field])
    op.create_index('uq_memory_removal_request_record','memory_removal_archives',['request_message_id','memory_id'],unique=True)


def downgrade():
    op.drop_table('memory_removal_archives')
