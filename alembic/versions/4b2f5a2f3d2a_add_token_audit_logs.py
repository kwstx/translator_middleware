"""Add token audit logs

Revision ID: 4b2f5a2f3d2a
Revises: 75c7e2369caa
Create Date: 2026-04-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4b2f5a2f3d2a"
down_revision: Union[str, Sequence[str], None] = "75c7e2369caa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "token_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_type", sa.String(), nullable=False),
        sa.Column("event_type", sa.Enum("ISSUED", "REFRESHED", "REVOKED", name="tokenauditevent"), nullable=False),
        sa.Column("jti", sa.String(), nullable=True),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("('{}'::jsonb)"), nullable=True),
        sa.Column("semantic_scopes", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("('{}'::jsonb)"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_token_audit_logs_event_type"), "token_audit_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_token_audit_logs_jti"), "token_audit_logs", ["jti"], unique=False)
    op.create_index(op.f("ix_token_audit_logs_token_type"), "token_audit_logs", ["token_type"], unique=False)
    op.create_index(op.f("ix_token_audit_logs_user_id"), "token_audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_token_audit_logs_user_id"), table_name="token_audit_logs")
    op.drop_index(op.f("ix_token_audit_logs_token_type"), table_name="token_audit_logs")
    op.drop_index(op.f("ix_token_audit_logs_jti"), table_name="token_audit_logs")
    op.drop_index(op.f("ix_token_audit_logs_event_type"), table_name="token_audit_logs")
    op.drop_table("token_audit_logs")
    op.execute("DROP TYPE IF EXISTS tokenauditevent")
