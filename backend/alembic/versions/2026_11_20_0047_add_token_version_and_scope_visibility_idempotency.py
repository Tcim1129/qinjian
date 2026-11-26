"""为用户增加令牌版本号并按操作人和记录收敛可见性幂等索引。"""

import sqlalchemy as sa
from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("users"):
        user_columns = {col["name"] for col in inspector.get_columns("users")}
        if "token_version" not in user_columns:
            op.add_column(
                "users",
                sa.Column(
                    "token_version",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                ),
            )

    if inspector.has_table("checkin_visibility_events"):
        existing_indexes = {
            idx["name"] for idx in inspector.get_indexes("checkin_visibility_events")
        }
        if "uq_checkin_visibility_events_client_request" in existing_indexes:
            op.drop_index(
                "uq_checkin_visibility_events_client_request",
                table_name="checkin_visibility_events",
            )
        op.create_index(
            "uq_checkin_visibility_events_client_request",
            "checkin_visibility_events",
            ["actor_user_id", "checkin_id", "client_request_id"],
            unique=True,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("checkin_visibility_events"):
        existing_indexes = {
            idx["name"] for idx in inspector.get_indexes("checkin_visibility_events")
        }
        if "uq_checkin_visibility_events_client_request" in existing_indexes:
            op.drop_index(
                "uq_checkin_visibility_events_client_request",
                table_name="checkin_visibility_events",
            )
        op.create_index(
            "uq_checkin_visibility_events_client_request",
            "checkin_visibility_events",
            ["client_request_id"],
            unique=True,
        )

    if inspector.has_table("users"):
        user_columns = {col["name"] for col in inspector.get_columns("users")}
        if "token_version" in user_columns:
            op.drop_column("users", "token_version")
