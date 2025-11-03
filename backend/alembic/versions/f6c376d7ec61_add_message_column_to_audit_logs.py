"""add_message_column_to_audit_logs

Revision ID: f6c376d7ec61
Revises: 79112e0c374c
Create Date: 2025-11-03 12:41:41.014609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6c376d7ec61'
down_revision: Union[str, Sequence[str], None] = '79112e0c374c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('audit_logs', sa.Column('message', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('audit_logs', 'message')
