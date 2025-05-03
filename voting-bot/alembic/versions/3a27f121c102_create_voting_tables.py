"""Create voting tables

Revision ID: 3a27f121c102
Revises: 
Create Date: 2025-04-22 18:17:40.271166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a27f121c102'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('telegram_id', sa.BigInteger, nullable=False, unique=True),
        sa.Column('username', sa.String(255)),
        sa.Column('role', sa.String(50), nullable=False, server_default='user')
    )

    # Create polls table
    op.create_table(
        'polls',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('creator_id', sa.BigInteger, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('end_time', sa.TIMESTAMP, nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='TRUE'),
        sa.ForeignKeyConstraint(['creator_id'], ['users.telegram_id'], ondelete='CASCADE')
    )

    # Create poll_options table
    op.create_table(
        'poll_options',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('poll_id', sa.Integer, nullable=False),
        sa.Column('option_text', sa.Text, nullable=False),
        sa.ForeignKeyConstraint(['poll_id'], ['polls.id'], ondelete='CASCADE')
    )

    # Create votes table
    op.create_table(
        'votes',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('poll_id', sa.Integer, nullable=False),
        sa.Column('user_id', sa.BigInteger, nullable=False),
        sa.Column('option_id', sa.Integer, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['poll_id'], ['polls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.telegram_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['option_id'], ['poll_options.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('poll_id', 'user_id')
    )


def downgrade():
    # Drop tables in reverse order of creation
    op.drop_table('votes')
    op.drop_table('poll_options')
    op.drop_table('polls')
    op.drop_table('users')