"""initial schema

Revision ID: 0adec3d37d25
Revises: 
Create Date: 2025-05-04 13:34:41.566147

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0adec3d37d25'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('calendar_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('season', sa.Integer(), nullable=False),
    sa.Column('round', sa.Integer(), nullable=False),
    sa.Column('session_type', sa.String(), nullable=False),
    sa.Column('start_ts', sa.DateTime(timezone=True), nullable=True),
    sa.Column('end_ts', sa.DateTime(timezone=True), nullable=True),
    sa.Column('meeting_key', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('lap_times',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('race_id', sa.String(), nullable=False),
    sa.Column('driver', sa.String(length=3), nullable=False),
    sa.Column('lap', sa.Integer(), nullable=True),
    sa.Column('lap_ms', sa.Integer(), nullable=True),
    sa.Column('compound', sa.String(length=10), nullable=True),
    sa.Column('stint_no', sa.Integer(), nullable=True),
    sa.Column('pit', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stints',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('race_id', sa.String(), nullable=False),
    sa.Column('driver', sa.String(length=3), nullable=False),
    sa.Column('stint_no', sa.Integer(), nullable=True),
    sa.Column('compound', sa.String(length=10), nullable=True),
    sa.Column('laps', sa.Integer(), nullable=True),
    sa.Column('avg_lap_ms', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('stints')
    op.drop_table('lap_times')
    op.drop_table('calendar_events')
    # ### end Alembic commands ###
