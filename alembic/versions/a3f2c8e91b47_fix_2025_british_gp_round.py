"""Fix 2025 British GP round numbering

British GP (meeting_key 1277) was incorrectly assigned to rounds 24 & 25.
It should be round 12 chronologically. This migration:
1. Shifts lap_times 2025-12 through 2025-23 to 2025-13 through 2025-24
2. Shifts stints similarly (if any data exists)
3. Fixes calendar_events: removes duplicates and corrects round numbers

Revision ID: a3f2c8e91b47
Revises: 9e0e89bdfe55
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f2c8e91b47'
down_revision: Union[str, None] = '9e0e89bdfe55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Shift lap_times from 2025-23 down to 2025-12, working backwards
    # to avoid conflicts (2025-23 -> 2025-24, then 2025-22 -> 2025-23, etc.)
    for old_round in range(23, 11, -1):  # 23, 22, 21, ..., 12
        new_round = old_round + 1
        op.execute(f"""
            UPDATE lap_times
            SET race_id = '2025-{new_round}'
            WHERE race_id = '2025-{old_round}'
        """)

    # Step 2: Shift stints similarly (in case any data exists)
    for old_round in range(23, 11, -1):
        new_round = old_round + 1
        op.execute(f"""
            UPDATE stints
            SET race_id = '2025-{new_round}'
            WHERE race_id = '2025-{old_round}'
        """)

    # Step 3: Fix calendar_events
    # First, delete the duplicate round 25 entry for British GP
    op.execute("""
        DELETE FROM calendar_events
        WHERE season = 2025 AND round = 25 AND meeting_key = 1277
    """)

    # Shift calendar rounds 12-23 to 13-24 (working backwards)
    for old_round in range(23, 11, -1):
        new_round = old_round + 1
        op.execute(f"""
            UPDATE calendar_events
            SET round = {new_round}
            WHERE season = 2025 AND round = {old_round}
        """)

    # Update the British GP entry from round 24 to round 12
    op.execute("""
        UPDATE calendar_events
        SET round = 12
        WHERE season = 2025 AND meeting_key = 1277
    """)


def downgrade() -> None:
    # Reverse the calendar fix first
    # Move British GP from round 12 back to round 24
    op.execute("""
        UPDATE calendar_events
        SET round = 24
        WHERE season = 2025 AND meeting_key = 1277
    """)

    # Shift calendar rounds 13-24 back to 12-23
    for old_round in range(13, 25):  # 13, 14, ..., 24
        new_round = old_round - 1
        op.execute(f"""
            UPDATE calendar_events
            SET round = {new_round}
            WHERE season = 2025 AND round = {old_round}
        """)

    # Re-insert the duplicate round 25 entry
    op.execute("""
        INSERT INTO calendar_events (season, round, session_type, start_ts, meeting_key)
        SELECT season, 25, session_type, start_ts, meeting_key
        FROM calendar_events
        WHERE season = 2025 AND meeting_key = 1277 AND round = 24
    """)

    # Shift lap_times back: 2025-13 through 2025-24 -> 2025-12 through 2025-23
    for old_round in range(13, 25):
        new_round = old_round - 1
        op.execute(f"""
            UPDATE lap_times
            SET race_id = '2025-{new_round}'
            WHERE race_id = '2025-{old_round}'
        """)

    # Shift stints back
    for old_round in range(13, 25):
        new_round = old_round - 1
        op.execute(f"""
            UPDATE stints
            SET race_id = '2025-{new_round}'
            WHERE race_id = '2025-{old_round}'
        """)
