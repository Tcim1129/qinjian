"""Version EmotiMirror consent receipts by purpose and artifact revision.

Revision ID: 0028
Revises: 0027
"""

from alembic import op
import sqlalchemy as sa


revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "emotimirror_consent_receipts",
        sa.Column(
            "purpose",
            sa.String(length=80),
            server_default="relationship_truce",
            nullable=False,
        ),
    )
    op.add_column(
        "emotimirror_consent_receipts",
        sa.Column("artifact_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_index(
        "ix_emotimirror_consent_receipts_purpose",
        "emotimirror_consent_receipts",
        ["purpose"],
    )
    op.create_index(
        "ix_emotimirror_consent_receipts_artifact_version",
        "emotimirror_consent_receipts",
        ["artifact_version"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_emotimirror_consent_receipts_artifact_version",
        table_name="emotimirror_consent_receipts",
    )
    op.drop_index(
        "ix_emotimirror_consent_receipts_purpose",
        table_name="emotimirror_consent_receipts",
    )
    op.drop_column("emotimirror_consent_receipts", "artifact_version")
    op.drop_column("emotimirror_consent_receipts", "purpose")
