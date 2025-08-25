"""remove_import_sessions_and_import_results_tables

Revision ID: 4e850865e33b
Revises: 7046b7dab74b
Create Date: 2025-08-25 02:06:15.386167

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e850865e33b'
down_revision: Union[str, Sequence[str], None] = '7046b7dab74b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop tables in correct order (respect foreign keys)
    op.drop_table('import_results')
    op.drop_table('import_sessions')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate tables if needed to rollback
    op.create_table('import_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('csv_url', sa.String(), nullable=False),
        sa.Column('login_url', sa.String(), nullable=False),
        sa.Column('billing_url', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_scheduled', sa.Boolean(), nullable=True),
        sa.Column('schedule_type', sa.String(), nullable=True),
        sa.Column('schedule_config', sa.JSON(), nullable=True),
        sa.Column('next_run', sa.DateTime(), nullable=True),
        sa.Column('last_scheduled_run', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('import_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('file_url', sa.String(), nullable=True),
        sa.Column('retry_attempts', sa.Integer(), nullable=True),
        sa.Column('final_error', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['import_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
