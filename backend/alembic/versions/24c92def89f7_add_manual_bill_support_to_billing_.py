"""add_manual_bill_support_to_billing_results

Revision ID: <will_be_generated>
Revises: 827ec51da280
Create Date: <will_be_generated>

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '<keep_the_generated_value>'
down_revision: Union[str, Sequence[str], None] = '827ec51da280'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns for manual bill uploads
    op.add_column('billing_results', sa.Column('original_filename', sa.String(), nullable=True))
    op.add_column('billing_results', sa.Column('provider_name', sa.String(), nullable=True))
    
    # Make user_billing_credential_id nullable to support manual uploads
    op.alter_column('billing_results', 'user_billing_credential_id',
                    existing_type=sa.String(),
                    nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert user_billing_credential_id to NOT NULL
    op.alter_column('billing_results', 'user_billing_credential_id',
                    existing_type=sa.String(),
                    nullable=False)
    
    # Drop the added columns
    op.drop_column('billing_results', 'provider_name')
    op.drop_column('billing_results', 'original_filename')