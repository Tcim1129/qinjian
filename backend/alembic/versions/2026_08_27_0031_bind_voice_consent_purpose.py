"""Bind the P4 voice consent to one narrow, acknowledged purpose.

Revision ID: 0031
Revises: 0030
"""

from alembic import op
import sqlalchemy as sa


revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "emotimirror_voice_consents",
        sa.Column(
            "purpose",
            sa.String(length=50),
            server_default="assistant_neutral_preview",
            nullable=False,
        ),
    )
    op.add_column(
        "emotimirror_voice_consents",
        sa.Column(
            "ai_synthetic_acknowledged",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_emotimirror_voice_consents_purpose",
        "emotimirror_voice_consents",
        ["purpose"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_emotimirror_voice_consents_purpose",
        table_name="emotimirror_voice_consents",
    )
    op.drop_column("emotimirror_voice_consents", "ai_synthetic_acknowledged")
    op.drop_column("emotimirror_voice_consents", "purpose")
