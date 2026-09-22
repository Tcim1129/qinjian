"""Add receiver consent and contact-level voice controls.

Revision ID: 0042
Revises: 0041
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emotimirror_voice_receiver_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receiver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=60), nullable=False),
        sa.Column("policy", sa.String(length=60), nullable=False),
        sa.Column("policy_version", sa.String(length=40), nullable=False),
        sa.Column("terms_version", sa.String(length=40), nullable=False),
        sa.Column("terms_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sender_id <> receiver_id", name="ck_voice_receiver_consent_distinct_users"),
        sa.CheckConstraint("status IN ('active','revoked')", name="ck_voice_receiver_consent_status"),
        sa.CheckConstraint("generation >= 1", name="ck_voice_receiver_consent_generation"),
        sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pair_id", "sender_id", "receiver_id", "purpose", name="uq_voice_receiver_consent_binding"),
    )
    op.create_index("ix_voice_receiver_consent_receiver_status", "emotimirror_voice_receiver_consents", ["receiver_id", "status"])
    op.create_index("ix_voice_receiver_consent_pair_sender", "emotimirror_voice_receiver_consents", ["pair_id", "sender_id"])

    op.create_table(
        "emotimirror_voice_contact_controls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receiver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sender_id <> receiver_id", name="ck_voice_contact_control_distinct_users"),
        sa.CheckConstraint("state IN ('allow','voice_disabled','blocked')", name="ck_voice_contact_control_state"),
        sa.CheckConstraint("generation >= 1", name="ck_voice_contact_control_generation"),
        sa.ForeignKeyConstraint(["pair_id"], ["pairs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pair_id", "sender_id", "receiver_id", name="uq_voice_contact_control_binding"),
    )
    op.create_index("ix_voice_contact_control_receiver_state", "emotimirror_voice_contact_controls", ["receiver_id", "state"])
    op.create_index("ix_voice_contact_control_pair_sender", "emotimirror_voice_contact_controls", ["pair_id", "sender_id"])


def downgrade() -> None:
    op.drop_index("ix_voice_contact_control_pair_sender", table_name="emotimirror_voice_contact_controls")
    op.drop_index("ix_voice_contact_control_receiver_state", table_name="emotimirror_voice_contact_controls")
    op.drop_table("emotimirror_voice_contact_controls")
    op.drop_index("ix_voice_receiver_consent_pair_sender", table_name="emotimirror_voice_receiver_consents")
    op.drop_index("ix_voice_receiver_consent_receiver_status", table_name="emotimirror_voice_receiver_consents")
    op.drop_table("emotimirror_voice_receiver_consents")
