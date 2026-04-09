"""add results column to tasks if missing

Revision ID: c8eaf587fd03
Revises: ab12cd34ef56
Create Date: 2026-04-09 19:46:33.002430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8eaf587fd03'
down_revision: Union[str, Sequence[str], None] = 'ab12cd34ef56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLModel/SQLAlchemy sometimes misses columns if they were added later
    # and the baseline was already applied. This ensures 'results' exists.
    # We use a raw execute for IF NOT EXISTS to avoid errors if it actually DOES exist now.
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS results JSONB DEFAULT '{}'::jsonb;")
    else:
        # For SQLite or others, we use try-except or just sa.Column via op.add_column.
        try:
            op.add_column('tasks', sa.Column('results', sa.JSON(), nullable=True, server_default='{}'))
        except Exception:
            # Column might already exist
            pass


def downgrade() -> None:
    pass
