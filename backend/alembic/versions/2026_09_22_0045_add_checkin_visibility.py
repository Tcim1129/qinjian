"""Add checkin visibility scope, optimistic version and append-only audit events.

Revision ID: 0045
Revises: 0044
Create Date: 2026-09-22 00:00:00.000000

Default scope follows the settled product decision: ``shared_summary``
(partner sees a de-identified summary, never the original text). ``private``
remains an explicit per-record opt-out.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '0045'
down_revision: Union[str, None] = '0044'
branch_labels = None
depends_on = None


def _identifier() -> sa.types.TypeEngine:
    return sa.CHAR(36).with_variant(postgresql.UUID(as_uuid=True), "postgresql")


def upgrade() -> None:
    identifier = _identifier()

    op.add_column(
        "checkins",
        sa.Column("visibility_scope", sa.String(length=20), nullable=False, server_default="shared_summary"),
    )
    op.add_column(
        "checkins",
        sa.Column("visibility_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("checkins", sa.Column("sharing_confirmed_at", sa.DateTime(), nullable=True))
    op.add_column("checkins", sa.Column("visibility_updated_at", sa.DateTime(), nullable=True))

    op.create_table(
        "checkin_visibility_events",
        sa.Column("id", identifier, primary_key=True),
        sa.Column(
            "checkin_id",
            identifier,
            sa.ForeignKey("checkins.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            identifier,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_scope", sa.String(length=20), nullable=True),
        sa.Column("to_scope", sa.String(length=20), nullable=False),
        sa.Column("from_version", sa.Integer(), nullable=True),
        sa.Column("to_version", sa.Integer(), nullable=False),
        sa.Column("sharing_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("client_request_id", sa.String(length=96), nullable=True),
        sa.Column("invalidated", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_checkin_visibility_events_checkin_created",
        "checkin_visibility_events",
        ["checkin_id", "created_at"],
    )
    op.create_index(
        "uq_checkin_visibility_events_client_request",
        "checkin_visibility_events",
        ["client_request_id"],
        unique=True,
    )

    op.create_table(
        "mobile_media_uploads",
        sa.Column("id", identifier, primary_key=True),
        sa.Column(
            "user_id",
            identifier,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_request_id", sa.String(length=96), nullable=False),
        sa.Column("media_kind", sa.String(length=10), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ready"),
        sa.Column("media_id", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_mobile_media_uploads_owner_request",
        "mobile_media_uploads",
        ["user_id", "client_request_id"],
        unique=True,
    )

    op.create_table(
        "mobile_offline_drafts",
        sa.Column("id", identifier, primary_key=True),
        sa.Column(
            "user_id",
            identifier,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_draft_id", sa.String(length=96), nullable=False),
        sa.Column(
            "relationship_space_id",
            identifier,
            sa.ForeignKey("pairs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "visibility_scope", sa.String(length=20), nullable=False, server_default="private"
        ),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("local_updated_at", sa.DateTime(), nullable=False),
        sa.Column("server_updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_mobile_offline_drafts_owner_draft",
        "mobile_offline_drafts",
        ["user_id", "client_draft_id"],
        unique=True,
    )

    op.create_table(
        "mobile_push_registrations",
        sa.Column("id", identifier, primary_key=True),
        sa.Column(
            "user_id",
            identifier,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("installation_id", sa.String(length=96), nullable=False),
        sa.Column("platform", sa.String(length=10), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False, server_default="unipush"),
        sa.Column("push_token", sa.String(length=255), nullable=True),
        sa.Column(
            "permission_state", sa.String(length=20), nullable=False, server_default="unknown"
        ),
        sa.Column(
            "registration_state",
            sa.String(length=20),
            nullable=False,
            server_default="unregistered",
        ),
        sa.Column("revocation_reason", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_mobile_push_registrations_owner_install",
        "mobile_push_registrations",
        ["user_id", "installation_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_mobile_push_registrations_owner_install", table_name="mobile_push_registrations")
    op.drop_table("mobile_push_registrations")
    op.drop_index("ix_mobile_offline_drafts_owner_draft", table_name="mobile_offline_drafts")
    op.drop_table("mobile_offline_drafts")
    op.drop_index("ix_mobile_media_uploads_owner_request", table_name="mobile_media_uploads")
    op.drop_table("mobile_media_uploads")
    op.drop_index("uq_checkin_visibility_events_client_request", table_name="checkin_visibility_events")
    op.drop_index("ix_checkin_visibility_events_checkin_created", table_name="checkin_visibility_events")
    op.drop_table("checkin_visibility_events")
    op.drop_column("checkins", "visibility_updated_at")
    op.drop_column("checkins", "sharing_confirmed_at")
    op.drop_column("checkins", "visibility_version")
    op.drop_column("checkins", "visibility_scope")
