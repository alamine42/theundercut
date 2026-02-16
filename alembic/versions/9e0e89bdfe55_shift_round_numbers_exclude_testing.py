"""shift_round_numbers_exclude_testing

Shift race_id round numbers down by 1 to align with calendar fix that
excludes pre-season testing. E.g., "2024-2" becomes "2024-1".

Revision ID: 9e0e89bdfe55
Revises: 5b1ed8f6a828
Create Date: 2026-02-16 17:18:38.643404

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e0e89bdfe55'
down_revision: Union[str, None] = '5b1ed8f6a828'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Shift round numbers down by 1 in lap_times and stints tables."""
    # Update lap_times: "YYYY-R" -> "YYYY-(R-1)"
    op.execute("""
        UPDATE lap_times
        SET race_id = SPLIT_PART(race_id, '-', 1) || '-' ||
                      (CAST(SPLIT_PART(race_id, '-', 2) AS INTEGER) - 1)::TEXT
        WHERE race_id ~ '^[0-9]{4}-[0-9]+$'
    """)

    # Update stints: same transformation
    op.execute("""
        UPDATE stints
        SET race_id = SPLIT_PART(race_id, '-', 1) || '-' ||
                      (CAST(SPLIT_PART(race_id, '-', 2) AS INTEGER) - 1)::TEXT
        WHERE race_id ~ '^[0-9]{4}-[0-9]+$'
    """)


def downgrade() -> None:
    """Shift round numbers back up by 1."""
    # Reverse: "YYYY-R" -> "YYYY-(R+1)"
    op.execute("""
        UPDATE lap_times
        SET race_id = SPLIT_PART(race_id, '-', 1) || '-' ||
                      (CAST(SPLIT_PART(race_id, '-', 2) AS INTEGER) + 1)::TEXT
        WHERE race_id ~ '^[0-9]{4}-[0-9]+$'
    """)

    op.execute("""
        UPDATE stints
        SET race_id = SPLIT_PART(race_id, '-', 1) || '-' ||
                      (CAST(SPLIT_PART(race_id, '-', 2) AS INTEGER) + 1)::TEXT
        WHERE race_id ~ '^[0-9]{4}-[0-9]+$'
    """)
